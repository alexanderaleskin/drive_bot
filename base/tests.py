from django.conf import settings
from telegram_django_bot.routing import telega_reverse
from telegram_django_bot.test import TD_TestCase
from telegram_django_bot.routing import RouterCallbackMessageCommandHandler

from .views import FolderViewSet, ShareLinkViewSet
from .models import Folder, MountInstance, ShareLink, User


class TestFolderViewSet(TD_TestCase):

    def setUp(self) -> None:
        user_id = int(settings.TELEGRAM_TEST_USER_IDS[0])
        self.user = User.objects.create(
            id=user_id,
            username=user_id
        )
        user_id2 = int(settings.TELEGRAM_TEST_USER_IDS[1]) 
        self.user2 = User.objects.create(
            id=user_id2,
            username=user_id2,
        )
        self.fvs = FolderViewSet(
            telega_reverse('base:FolderViewSet'),
            user=self.user,
            bot=self.test_callback_context.bot
        )
        self.fvs_user2 = FolderViewSet(
            telega_reverse('base:FolderViewSet'),
            user=self.user2,
            bot=self.test_callback_context.bot
        )
        self.root_folder = Folder.objects.get(
            user_id=user_id,
            parent__isnull=True
        )
        self.root_folder_user2 = Folder.objects.get(
            user_id=user_id2,
            parent__isnull=True
        )

        self.rc_mch = RouterCallbackMessageCommandHandler()
        self.handle_update = lambda update: self.rc_mch.handle_update(
            update, 'some_str', 'some_str', self.test_callback_context
        )

    def create_folder_for_user(self):
        self.fvs.create('parent', self.root_folder.pk)
        self.fvs.create('name', 'some_folder1')
        folder = Folder.objects.get(
            user_id=self.user.id,
            parent=self.root_folder,
            name='some_folder1',
        )

        return folder

    def create_share_link_for_user(self, folder_pk, type_link, share_amount):
        sl = ShareLinkViewSet(
            telega_reverse('base:ShareLinkViewSet'),
            user=self.user,
            bot=self.test_callback_context.bot
        )
        sl.foreign_filters = [folder_pk, '']
        sl.create('type_link', type_link)
        sl.create('share_amount', share_amount)
        share_link = ShareLink.objects.get(
            folder_id=folder_pk,
            share_amount=share_amount,
        )

        return share_link

    def test_generate_links(self):
        self.assertEqual(
            f'fol/cr&parent&{self.root_folder.pk}',
            self.fvs.gm_callback_data('create', 'parent', self.root_folder.pk)
        )

    def test_create_folder(self):
        folder = self.create_folder_for_user()

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
        self.assertEqual(5, len(buttons))
        self.assertEqual(f'fol/up&{created_folder.pk}&name', buttons[0][0]['callback_data'])
        self.assertEqual(f'fol/sl&{created_folder.pk}', buttons[4][0]['callback_data'])

    def test_show_elem_user_clicks(self):

        start_send = self.create_update({'text': '/start'})
        res_message = self.handle_update(start_send)

        add_folder = self.create_update(
            res_message.to_dict(), {'data': f'fol/cr&parent&{self.root_folder.pk}'}
        )
        res_message = self.handle_update(add_folder)

        write_folder_name = self.create_update({'text': 'some_folder'})
        res_message = self.handle_update(write_folder_name)

        created_folder = Folder.objects.get(
            user_id=self.user.id,
            parent=self.root_folder,
            name='some_folder',
        )

        show_folder = self.create_update(
            res_message.to_dict(), {'data': f'fol/se&{created_folder.pk}'}
        )
        res_message = self.handle_update(show_folder)

        buttons = res_message.reply_markup.to_dict()['inline_keyboard']
        self.assertEqual(5, len(buttons))
        self.assertEqual(f'fol/up&{created_folder.pk}&name', buttons[0][0]['callback_data'])
        self.assertEqual(f'change_location/{created_folder.pk}/Folder', buttons[1][0]['callback_data'])
        self.assertEqual(f'sl/sl&{created_folder.pk}&', buttons[2][0]['callback_data'])
        self.assertEqual(f'fol/de&{created_folder.pk}', buttons[3][0]['callback_data'])
        self.assertEqual(f'fol/sl&{created_folder.pk}', buttons[4][0]['callback_data'])

    def test_show_elem(self):
        folder = self.create_folder_for_user()

        __, (mess, buttons) = self.fvs.show_elem(folder.pk)
        edit_title, change_location, share_folder, delete_but, back_but = buttons

        edit_title = edit_title[0].to_dict()
        self.assertEqual(edit_title['callback_data'], f'fol/up&{folder.pk}&name')
        self.assertEqual(edit_title['text'], '📝 Title')

        change_location = change_location[0].to_dict()
        self.assertEqual(change_location['callback_data'], f'change_location/{folder.pk}/Folder')
        self.assertEqual(change_location['text'], '🗺 Change location')

        share_folder = share_folder[0].to_dict()
        self.assertEqual(share_folder['callback_data'], f'sl/sl&{folder.pk}&')
        self.assertEqual(share_folder['text'], '🔗 General access')

        delete_but = delete_but[0].to_dict()
        self.assertEqual(delete_but['callback_data'], f'fol/de&{folder.pk}')
        self.assertEqual(delete_but['text'], '❌ Delete')

        back_but = back_but[0].to_dict()
        self.assertEqual(back_but['callback_data'], f'fol/sl&{folder.pk}')
        self.assertEqual(back_but['text'], '🔙 Back')
        
    def test_show_list_created_folder(self):
        folder = self.create_folder_for_user()

        __, (mess, buttons) = self.fvs.show_list(folder.pk)
        add_folder_but, add_file_but, edit_folder_but = buttons[0]
        back_but = buttons[1][0]

        add_file_but = add_file_but.to_dict()
        self.assertEqual(add_file_but['text'], '➕ File')
        self.assertEqual(add_file_but['callback_data'], f'fl/cr&folder&{folder.pk}')

        add_folder_but = add_folder_but.to_dict()
        self.assertEqual(add_folder_but['text'], '➕ Folder')
        self.assertEqual(add_folder_but['callback_data'], f'fol/cr&parent&{folder.pk}')

        edit_folder_but = edit_folder_but.to_dict()
        self.assertEqual(edit_folder_but['text'], f'⚙️ {folder.name}')
        self.assertEqual(edit_folder_but['callback_data'], f'fol/se&{folder.pk}')

        back_but = back_but.to_dict()
        self.assertEqual(back_but['text'], '🔙 Back')
        self.assertEqual(back_but['callback_data'], f'fol/sl&{self.root_folder.pk}')

    def test_start_with_share_link_only_show_for_folder(self):
        folder = self.create_folder_for_user()        
        share_link = self.create_share_link_for_user(folder.pk, 'S', 1)

        start_send = self.create_update(
            {'text': f'/start {share_link.share_code}'},
            user_id=self.user2.id
        )
        res_message = self.handle_update(start_send)

        __, (mess, buttons) = self.fvs_user2.show_list(folder.pk)
        # buttons: edit_folder_but, back_but
        self.assertEqual(len(buttons), 2)

        __, (mess, buttons) = self.fvs_user2.show_elem(folder.pk)
        status = mess.splitlines()[-1].strip()
        self.assertEqual(status, 'Public folder: 🌍 Yes')
        self.assertEqual(len(buttons), 4)

        change_name = self.create_update(
            res_message.to_dict(),
            {'data': f'fol/up&{folder.pk}&name&folder'},
            user_id=self.user2.id
        )
        res_message = self.handle_update(change_name)
        
        self.assertEqual(
            'Sorry, you do not have permissions to this action.',
            res_message.text,
        )
        self.assertEqual('some_folder1', folder.name)

    def test_start_with_share_link_show_change_for_folder(self):
        folder = self.create_folder_for_user()        
        share_link = self.create_share_link_for_user(folder.pk, 'C', 1)

        start_send = self.create_update(
            {'text': f'/start {share_link.share_code}'},
            user_id=self.user2.id
        )
        res_message = self.handle_update(start_send)

        __, (mess, buttons) = self.fvs_user2.show_elem(folder.pk)
        # buttons: edit_title, change_location, delete_but, back_but
        status = mess.splitlines()[-1].strip()
        self.assertEqual(status, 'Public folder: 🌍 Yes')
        self.assertEqual(len(buttons), 4)

        __, (mess, buttons) = self.fvs_user2.show_list(folder.pk)
        # buttons: add_folder_but, add_file_but, edit_folder_but, back_but
        self.assertEqual(len(buttons[0]) + len(buttons[1]), 4) 

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
        self.assertEqual(add_file_but['text'], '➕ File')
        self.assertEqual(add_file_but['callback_data'], f'fl/cr&folder&{self.root_folder.pk}')

        add_folder_but = add_folder_but.to_dict()
        self.assertEqual(add_folder_but['text'], '➕ Folder')
        self.assertEqual(add_folder_but['callback_data'], f'fol/cr&parent&{self.root_folder.pk}')
