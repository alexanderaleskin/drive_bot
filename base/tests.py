from django.conf import settings
from telegram_django_bot.routing import telega_reverse
from telegram_django_bot.test import TD_TestCase

from .views import FolderViewSet
from .models import Folder, User


class TestFolderViewSet(TD_TestCase):

    def setUp(self) -> None:
        user_id = int(settings.TELEGRAM_USER_ID)
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

    def test_generate_links(self):
        self.assertEqual(
            f'fol/cr&parent&{self.root_folder.pk}',
            self.fvs.gm_callback_data('create', 'parent', self.root_folder.pk)
        )

    def test_create_folder(self):
        self.fvs.create('parent', self.root_folder.pk)
        self.fvs.create('name', 'papka')
        folder = Folder.objects.get(
            user_id=self.user.id,
            parent=self.root_folder,
        )

        self.assertEqual(folder.name, 'papka')
        self.assertEqual(folder.parent.pk, self.root_folder.pk)
        self.assertEqual(folder.user.id, self.user.id)
