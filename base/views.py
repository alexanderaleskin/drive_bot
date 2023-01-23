import copy

from django.conf import settings
from telegram_django_bot.models import MESSAGE_FORMAT
from telegram_django_bot.routing import telega_reverse
from telegram_django_bot.telegram_lib_redefinition import InlineKeyboardButtonDJ
from telegram_django_bot.td_viewset import TelegaViewSet
from telegram_django_bot.utils import handler_decor
from telegram_django_bot.tg_dj_bot import TG_DJ_Bot

from django.utils.translation import gettext as _

from telegram import Update

from .models import User, File, Folder
from .forms import FileForm, FolderForm


@handler_decor()
def start(bot: TG_DJ_Bot, update: Update, user: User):
    root_folder = Folder.objects.filter(
        user_id=user.id,
        parent=None
    ).first()

    message = (
        f'Привет {user.first_name or user.telegram_username or user.id}!\n'
        'Я работаю все ок!\n'
    )
    buttons = [
        [
            InlineKeyboardButtonDJ(
                text=_('🧩 BotMenu'),
                callback_data=FolderViewSet(
                    telega_reverse('base:FolderViewSet')
                ).gm_callback_data('show_list', root_folder.pk)
            ),
        ]
    ]
    
    return bot.edit_or_send(update, message, buttons)


class FolderViewSet(TelegaViewSet):
    telega_form = FolderForm
    queryset = Folder.objects.all()
    viewset_name = 'FolderViewSet'
    updating_fields = ['name', 'file']

    def get_queryset(self):
        queryset = super().get_queryset()

        return queryset.filter(
            user_id=self.user.id,
        )

    def delete(self, model_or_pk, is_confirmed=False):
        model = self._get_elem(model_or_pk)

        if model:
            __, (mess, buttons) = super().delete(model_or_pk, is_confirmed)
            button_to_back = [
                InlineKeyboardButtonDJ(
                    text=_('🔙 Return to list'),
                    callback_data=self.gm_callback_data(
                        'show_list',
                        model.parent.id
                    )
                )
            ]
            buttons = buttons[:-1]
            buttons.append(button_to_back)

            return self.CHAT_ACTION_MESSAGE, (mess, buttons)
        else:
            return self.generate_message_no_elem(model_or_pk)

    
    def create(self, field=None, value=None):
        initial_data = {'user': self.user.id}

        if field is None and value is None:
            self.user.clear_status(commit=False)
        else:
            initial_data = {
                'user': self.user.id,
            }

        return self.create_or_update_helper(
            field, value, 'create', initial_data=initial_data
        )

    def show_elem(self, model_or_pk, mess=''):
        model = self._get_elem(model_or_pk)

        if model:
            return self.show_list(model.pk)
        else:
            return super().show_elem(model_or_pk)

    def show_list(self, folder_id, page=0, per_page=10, columns=1):
        """show list items"""

        current_folder = Folder.objects.get(
            user_id=self.user.id,
            pk=folder_id
        )
        file_queryset = list(
            File.objects.filter(
                user_id=self.user.id,
                folder_id=folder_id
            )
        )
        count_subfolder = len(
            self.get_queryset().filter(
                user_id=self.user.id,
                parent=current_folder
            )
        )
        count_file = len(file_queryset)

        # import pdb;pdb.set_trace()
        mess = ''
        buttons = []
        page = int(page)
        
        count_models = count_file + count_subfolder
        first_this_page = page * per_page * columns
        first_next_page = (page + 1) * per_page * columns
        
        models = list(
            self.get_queryset()
            .filter(parent=current_folder)
            [first_this_page: first_next_page]
        ) + file_queryset

        prev_page_button = InlineKeyboardButtonDJ(
            text=f'◀️️️ ',
            callback_data=self.generate_message_callback_data(
                self.command_routings['command_routing_show_list'],
                folder_id, str(page - 1)
            )
        )
        next_page_button = InlineKeyboardButtonDJ(
            text=f'▶️️ ',
            callback_data=self.generate_message_callback_data(
                self.command_routings['command_routing_show_list'],
                folder_id, str(page + 1),
            )
        )

        if len(models) < count_models:
            if (first_this_page > 0) and (first_next_page < count_models):
                buttons = [[prev_page_button, next_page_button]]
            elif first_this_page == 0:
                buttons = [[next_page_button]]
            elif first_next_page >= count_models:
                buttons = [[prev_page_button]]
            else:
                print(f'unreal situation {count_models}, \
                    {len(models)}, {first_this_page}, {first_next_page}')

        if current_folder.parent:
            buttons += [
                self.generate_show_list_back_button(current_folder.parent)
            ]

        buttons += self.generate_show_list_static_button(current_folder)

        if len(models):
            mess += (
                f'Folder: {current_folder.name}\n'
                f'Subfolder: {count_subfolder}\n'
                f'Files: {count_file}\n'
                f'Date time change: {current_folder.datetime_change}'
            )
            for it_m, model in enumerate(models, page * per_page * columns + 1):
                buttons += [
                    self.get_show_elem_button(model, folder_id)
                ]
        else:
            mess = _('There is nothing to show.')

        return self.CHAT_ACTION_MESSAGE, (mess, buttons)

    def generate_show_list_static_button(self, model):
        buttons = [
            [
                InlineKeyboardButtonDJ(
                    text=_('➕ Add folder'),
                    callback_data=self.gm_callback_data(
                        'create', 'parent', model.id
                    )
                ),
            ],
            [
                InlineKeyboardButtonDJ(
                    text=_('➕ Add file'),
                    callback_data=FileViewSet(
                        telega_reverse('base:FileViewSet')
                    ).gm_callback_data('create', 'folder', model.id)
                )
            ]
        ]

        return buttons

    def show_edit_folder(self, model_or_pk, mess=''):
        model = self._get_elem(model_or_pk)

        if model:
            count_subfolder = Folder.objects.filter(
                user_id=self.user.id,
                parent_id=model.pk
            ).count()
            count_files = File.objects.filter(
                user_id=self.user.id,
                folder_id=model.pk
            )
            mess += _(
                f'Folder: {model.name}\n'
                f'SubFolders: {count_subfolder}\n'
                f'Files: {count_files}\n'
                f'Date time change: {model.datetime_change}\n'
            )
            buttons = [
                [
                    InlineKeyboardButtonDJ(
                        text=_('📝 name'),
                        callback_data=self.gm_callback_data(
                            'change', model.id, 'name'
                        )
                    )
                ],
                [
                    InlineKeyboardButtonDJ(
                        text=_('🔙 Back'),
                        callback_data=self.gm_callback_data(
                            'show_list', model.pk
                        )
                    )
                ]
            ]

            return self.CHAT_ACTION_MESSAGE, (mess, buttons)
        else:
            return self.generate_message_no_elem(model_or_pk)

    def generate_show_list_back_button(self, model_parent):
        button = [
            InlineKeyboardButtonDJ(
                text=_('🔙 Back'),
                callback_data=self.gm_callback_data(
                    'show_list', model_parent.pk
                )
            )
        ]

        return button

    def get_show_elem_button(self, model, folder_id):

        if isinstance(model, Folder):
            button = [
                InlineKeyboardButtonDJ(
                    text=self.get_model_name(model),
                    callback_data=self.gm_callback_data(
                        'show_list', model.pk
                    )
                )
            ]

            return button
        else:
            button = [
                InlineKeyboardButtonDJ(
                    text=self.get_model_name(model),
                    callback_data=FileViewSet(
                        telega_reverse('base:FileViewSet')
                    ).gm_callback_data('show_elem', folder_id, model.pk)
                )
            ]

            return button

    def get_model_name(self, model):
        
        if isinstance(model, Folder):
            return _(f'📁 {model.name}')
        else:
            return _(f'📔 {model.message_format}')

    def generate_message_self_variant(
        self, field_name, mess='', func_response='create',instance_id=None):
        __, (message, buttons) = super().generate_message_self_variant(
            field_name, str(mess), func_response, instance_id
        )

        if field_name == 'name':
            mess += _(
                'Напишите имя новой папки'
            )
        else:
            mess = message

        return self.CHAT_ACTION_MESSAGE, (mess, buttons)



class FileViewSet(TelegaViewSet):
    telega_form = FileForm
    queryset = File.objects.all()
    viewset_name = 'FileViewSet'
    updating_fields = ['text', 'media_id']

    def create(self, field=None, value=None):
        
        if field is None and value is None:
            self.user.clear_status(commit=False)

        initial_data = {
            'user': self.user.id,
        }

        return self.create_or_update_helper(
            field, value, 'create', initial_data=initial_data
        )

    def create_or_update_helper(
            self, field, value, func_response='create',
            instance=None, initial_data=None):

        initial_data = {} if initial_data is None \
                            else copy.deepcopy(initial_data)

        if field == 'media_id' and (message := self.update.message):
            caption = True
            if message.photo:
                initial_data = {
                    'message_format': MESSAGE_FORMAT.PHOTO,
                    'media_id': message.photo[-1]['file_id'],
                }
            elif message.audio:
                initial_data = {
                    'message_format': MESSAGE_FORMAT.AUDIO,
                    'media_id': message.audio['file_id'],
                }
            elif message.document:
                initial_data = {
                    'message_format': MESSAGE_FORMAT.DOCUMENT,
                    'media_id': message.document['file_id'],
                }
            elif message.sticker:
                initial_data = {
                    'message_format': MESSAGE_FORMAT.STICKER,
                    'media_id': message.sticker['file_id'],
                }
            elif message.video:
                initial_data = {
                    'message_format': MESSAGE_FORMAT.VIDEO,
                    'media_id': message.video['file_id'],
                }
            elif message.animation:
                initial_data = {
                    'message_format': MESSAGE_FORMAT.GIF,
                    'media_id': message.animation['file_id'],
                }
            elif message.voice:
                initial_data = {
                    'message_format': MESSAGE_FORMAT.VOICE,
                    'media_id': message.voice['file_id'],
                }
            elif message.video_note:
                initial_data = {
                    'message_format': MESSAGE_FORMAT.VIDEO_NOTE,
                    'media_id': message.video_note['file_id'],
                }
            elif message.media_group_id:
                raise NotImplementedError('')

            elif message.location:
                initial_data = {
                    'message_format': MESSAGE_FORMAT.LOCATION,
                    'media_id': message.location['file_id'],
                }
            else:
                caption = False
                initial_data = {
                    'message_format': MESSAGE_FORMAT.TEXT,
                    'media_id': '',
                    'text': message.text,
                }

            if caption:
                initial_data['text'] = message.caption

            initial_data['user'] = message.from_user.id

        if field == 'text' and (message := self.update.message) and message.text:
            initial_data['text'] = message.text

        result = super().create_or_update_helper(
            field, value, func_response, instance, initial_data
        )

        return result

    def show_list(self, page=0, per_page=10, columns=1):
        __, (mess, buttons) = super().show_list(page, per_page, columns)
        buttons += [
            [
                InlineKeyboardButtonDJ(
                    text=_('➕ Add file'),
                    callback_data=self.gm_callback_data('create')
                )
            ],
            [
                InlineKeyboardButtonDJ(
                    text=_('🔙 Back'),
                    callback_data=FolderViewSet(
                        telega_reverse('base:FolderViewSet')
                    ).gm_callback_data('show_elem', self.foreign_filters[0])
                )
            ],
        ]

        return self.CHAT_ACTION_MESSAGE, (mess, buttons)

    def generate_message_self_variant(
        self, field_name, mess='', func_response='create', instance_id=None):

        __, (message, buttons) = super().generate_message_self_variant(
            field_name, str(mess), func_response, instance_id
        )

        if field_name == 'media_id':
            mess += _(
                'Пожалуйста отправьте файл 👇'
            )
        elif field_name == 'text':
            mess += _(
                'Введите сообщение'
            )
        else:
            mess = message

        return self.CHAT_ACTION_MESSAGE, (mess, buttons)

    def generate_elem_buttons(self, model, elem_per_raw=2):
        buttons = [
            [
                InlineKeyboardButtonDJ(
                    text=_('🖼 Media'),
                    callback_data=self.gm_callback_data(
                        'change', model.id, 'media_id'
                    )
                ),
            ],
            [
                InlineKeyboardButtonDJ(
                    text=_('📝 text'),
                    callback_data=self.gm_callback_data(
                        'change', model.id, 'text'
                    )
                ),
            ],
            [
                InlineKeyboardButtonDJ(
                    text=_('❌ Delete'),
                    callback_data=self.gm_callback_data(
                        'delete', model.id
                    )
                ),
            ],
            [
                InlineKeyboardButtonDJ(
                    text=_('🔙 Back'),
                    callback_data=FolderViewSet(
                        telega_reverse('base:FolderViewSet')
                    ).gm_callback_data('show_elem', model.folder.id)
                ),
            ],
        ]

        return buttons


    def send_file_from_model(self, model, chat_id):

        return self.bot.send_format_message(
            message_format=model.message_format,
            text=model.text,
            media_files_list=[model.media_id],
            update=self.update,
            only_send=True,
            chat_id=chat_id,
        )

    def show_elem(self, model_or_pk, mess=''):
        model = self._get_elem(model_or_pk)
        
        if model:
            self.send_file_from_model(model, self.user.id)
        
        self.update.callback_query = None

        return super().show_elem(model_or_pk, mess)
