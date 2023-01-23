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
                ).gm_callback_data('show_elem', root_folder.pk)
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
        """delete item"""

        # import pdb;pdb.set_trace()
        model = self._get_elem(model_or_pk)
        model_parent = model.parent

        if model:
            buttons = []

            if self.deleting_with_confirm and not is_confirmed:
                # just ask for confirmation
                mess = self.show_texts_dict['confirm_deleting'] % {
                    'viewset_name': model.name,
                    'model_id': f'#{model.id}' or '',
                }
                buttons = [
                    [InlineKeyboardButtonDJ(
                        text=self.show_texts_dict['confirm_delete_button_text'],
                        callback_data=self.gm_callback_data(
                            'delete',
                            model.id,
                            '1'  # True
                        )
                    )]
                ]
                if 'show_elem' in self.actions:
                    buttons += [
                        [InlineKeyboardButtonDJ(
                            text=_('🔙 Back'),
                            callback_data=self.gm_callback_data(
                                'show_elem',
                                model.id,
                            )
                        )]
                    ]

            else:
                # real deleting
                model.delete()

                mess = self.show_texts_dict['succesfully_deleted'] % {
                    'viewset_name': model.name,
                    'model_id': f'#{model.id}' or '',
                }

                if 'show_list' in self.actions:
                    buttons += [
                        [InlineKeyboardButtonDJ(
                            text=_('🔙 Return to list'),
                            callback_data=self.gm_callback_data(
                                'show_elem',
                                model_parent.id
                            )
                        )]
                    ]
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

    def show_list(self, page=0, per_page=10, columns=1):
        __, (mess, buttons) = super().show_list(page, per_page, columns)
        buttons += [
            [
                InlineKeyboardButtonDJ(
                    text=_('➕ Add'),
                    callback_data=self.gm_callback_data('create',)
                ),
            ],
            [
                InlineKeyboardButtonDJ(
                    text=_('🔙 Back'),
                    callback_data=settings.TELEGRAM_BOT_MAIN_MENU_CALLBACK
                )
            ]
        ]

        return self.CHAT_ACTION_MESSAGE, (mess, buttons)

    def show_elem(self, model_or_pk, mess=''):
        model = self._get_elem(model_or_pk)

        if model:
            if self.use_name_and_id_in_elem_showing:
                mess += f'{model.name} #{model.pk} \n'

            mess += self.generate_show_fields(model, full_show=True)
            buttons = self.generate_elem_buttons(model)
            folder_queryset = Folder.objects.filter(
                parent_id=model.id,
                user_id=self.user.id
            )

            if folder_queryset:
                for folder in folder_queryset:

                    button = [
                        InlineKeyboardButtonDJ(
                            text=_(f'Папка {folder.name}'),
                            callback_data=self.gm_callback_data(
                                'show_elem', folder.pk
                            )
                        )
                    ]
                    buttons.append(button)

            return self.CHAT_ACTION_MESSAGE, (mess, buttons)
        else:
            return self.generate_message_no_elem(model_or_pk)

    def generate_elem_buttons(self, model, elem_per_raw=2):

        model_parent = model.parent.pk if model.parent else None
        
        buttons = [
            [
                InlineKeyboardButtonDJ(
                    text=_('🖼 Files'),
                    callback_data=FileViewSet(
                        telega_reverse('base:FileViewSet')
                    ).gm_callback_data('show_list', model.id)
                ),
            ],
            [
                InlineKeyboardButtonDJ(
                    text=_('📝 name'),
                    callback_data=self.gm_callback_data('change', model.id, 'name')
                ),
            ],
            [
                InlineKeyboardButtonDJ(
                    text=_('➕ Add folder'),
                    callback_data=self.gm_callback_data('create', 'parent', model.id)
                ),
            ],
        ]

        if model_parent:
            button_del = [
                InlineKeyboardButtonDJ(
                    text=_('❌ Delete'),
                    callback_data=self.gm_callback_data('delete', model.id)
                ),
            ]
            button_back = [
                InlineKeyboardButtonDJ(
                    text=_('🔙 Back'),
                    callback_data=FolderViewSet(
                        telega_reverse('base:FolderViewSet')
                    ).gm_callback_data('show_elem', model_parent)
                ),
            ]
            buttons.append(button_del)
            buttons.append(button_back)

        return buttons

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
    foreign_filter_amount = 1

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            user_id=self.user.id,
            folder_id=self.foreign_filters[0]
        )

        return queryset

    def create(self, field=None, value=None):
        
        if field is None and value is None:
            self.user.clear_status(commit=False)

        initial_data = {
            'user': self.user.id,
            'folder': self.foreign_filters[0]
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
