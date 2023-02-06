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
        self.fvs.create('name', 'some_folder1')
        folder = Folder.objects.get(
            user_id=self.user.id,
            parent=self.root_folder,
            name='some_folder1',
        )

        self.assertEqual(folder.name, 'some_folder1')
        self.assertEqual(folder.parent.pk, self.root_folder.pk)
        self.assertEqual(folder.user.id, self.user.id)


    def test_create_folder_user_clicks(self):

        start_send = self.create_update({'text': '/start'})
        res_message = self.handle_update(start_send)

        action_add_folder = self.create_update(
            res_message.to_dict(), {'data': f'fol/cr&parent&{self.root_folder.pk}'}
        )
        res_message = self.handle_update(action_add_folder)

        write_folder_name = self.create_update({'text': 'some_folder2'})
        res_message = self.handle_update(write_folder_name)

        created_folder = Folder.objects.get(
            user_id=self.user.id,
            parent=self.root_folder,
            name='some_folder2',
        )

        self.assertEqual(created_folder.name, 'some_folder2')
        self.assertEqual(created_folder.user.id, self.user.id)

        buttons = res_message.reply_markup.to_dict()['inline_keyboard']
        self.assertEqual(4, len(buttons))
        self.assertEqual(f'fol/up&{created_folder.id}&name', buttons[0][0]['callback_data'])
        self.assertEqual(f'fol/sl&{created_folder.id}', buttons[3][0]['callback_data'])

    def test_show_elem(self):
        self.fvs.create('parent', self.root_folder.pk)
        self.fvs.create('name', 'some_folder1')
        folder = Folder.objects.get(
            user_id=self.user.id,
            parent=self.root_folder,
            name='some_folder1',
        )
        __, (mess, buttons) = self.fvs.show_elem(folder.pk)
        edit_title, share_folder, delete_but, back_but = buttons

        edit_title = edit_title[0].to_dict()
        self.assertEqual(edit_title['callback_data'], f'fol/up&{folder.id}&name')
        self.assertEqual(edit_title['text'], '📝 Title')

        share_folder = share_folder[0].to_dict()
        self.assertEqual(share_folder['callback_data'], f'sl/sl&{folder.pk}&')
        self.assertEqual(share_folder['text'], '🔗 General access')

        delete_but = delete_but[0].to_dict()
        self.assertEqual(delete_but['callback_data'], f'fol/de&{folder.pk}')
        self.assertEqual(delete_but['text'], '❌ Delete')

        back_but = back_but[0].to_dict()
        self.assertEqual(back_but['callback_data'], f'fol/sl&{folder.pk}')
        self.assertEqual(back_but['text'], '🔙 Back')
        

    def test_show_list_user_clicks(self):
        
        start_send = self.create_update({'text': '/start'})
        res_message = self.handle_update(start_send)

        buttons = res_message.reply_markup.to_dict()['inline_keyboard']
        self.assertEqual(f'fol/cr&parent&{self.root_folder.pk}', buttons[0][0]['callback_data'])
        self.assertEqual(f'fl/cr&folder&{self.root_folder.pk}', buttons[0][1]['callback_data'])
        self.assertEqual(f'us/se', buttons[1][0]['callback_data'])

    def test_show_list(self):
        __, (mess, buttons) = self.fvs.show_list(self.root_folder.pk)
        add_folder_but, add_file_but = buttons[0]

        add_file_but = add_file_but.to_dict()
        self.assertEqual(add_file_but['text'], '➕ Add file')
        self.assertEqual(add_file_but['callback_data'], f'fl/cr&folder&{self.root_folder.pk}')

        add_folder_but = add_folder_but.to_dict()
        self.assertEqual(add_folder_but['text'], '➕ Add folder')
        self.assertEqual(add_folder_but['callback_data'], f'fol/cr&parent&{self.root_folder.pk}')
