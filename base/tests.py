from django.conf import settings
from telegram_django_bot.routing import telega_reverse
from telegram_django_bot.test import TD_TestCase
from telegram_django_bot.routing import RouterCallbackMessageCommandHandler

from .views import FolderViewSet
from .models import Folder, User


class TestFolderViewSet(TD_TestCase):

    def setUp(self) -> None:
        user_id = int(settings.TELEGRAM_TEST_USER_IDS[0])
        self.user = User.objects.create(
            id=user_id,
            username=user_id
        )
        self.fvs = FolderViewSet(
            telega_reverse('base:FolderViewSet'),
            user=self.user,
            bot=self.test_callback_context.bot
        )
        self.root_folder = Folder.objects.get(
            user_id=user_id,
            parent__isnull=True
        )

        self.rc_mch = RouterCallbackMessageCommandHandler()
        self.handle_update = lambda update: self.rc_mch.handle_update(
            update, 'some_str', 'some_str', self.test_callback_context
        )


    def test_generate_links(self):
        self.assertEqual(
            f'fol/cr&parent&{self.root_folder.pk}',
            self.fvs.gm_callback_data('create', 'parent', self.root_folder.pk)
        )

    def test_create_folder(self):
        self.fvs.create('parent', self.root_folder.pk)
        self.fvs.create('name', 'some_folder')
        folder = Folder.objects.get(
            user_id=self.user.id,
            parent=self.root_folder,
        )

        self.assertEqual(folder.name, 'some_folder')
        self.assertEqual(folder.parent.pk, self.root_folder.pk)
        self.assertEqual(folder.user.id, self.user.id)


    def test_create_folder_user_clicks(self):

        start_send = self.create_update({'text': '/start'})
        res_message = self.handle_update(start_send)

        action_add_folder = self.create_update(res_message.to_dict(), {'data': f'fol/cr&parent&{self.root_folder.pk}'})
        res_message = self.handle_update(action_add_folder)

        write_folder_name = self.create_update({'text': 'some_folder'})
        res_message = self.handle_update(write_folder_name)

        created_folder = Folder.objects.get(
            user_id=self.user.id,
            parent=self.root_folder,
        )

        self.assertEqual(created_folder.name, 'some_folder')
        self.assertEqual(created_folder.user.id, self.user.id)

        buttons = res_message.reply_markup.to_dict()['inline_keyboard']
        self.assertEqual(4, len(buttons))
        self.assertEqual(f'fol/up&{created_folder.id}&name', buttons[0][0]['callback_data'])
        self.assertEqual(f'fol/sl&{created_folder.id}', buttons[3][0]['callback_data'])
