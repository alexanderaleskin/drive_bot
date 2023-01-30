import copy
from uuid import uuid4
from django.conf import settings

from telegram_django_bot.models import MESSAGE_FORMAT
from telegram_django_bot.routing import telega_reverse
from telegram_django_bot.telegram_lib_redefinition import InlineKeyboardButtonDJ, InlineKeyboardMarkupDJ
from telegram_django_bot.td_viewset import TelegaViewSet
from telegram_django_bot.utils import handler_decor
from telegram_django_bot.tg_dj_bot import TG_DJ_Bot

from django.utils.translation import gettext as _, gettext_lazy
from django.db.models import Count, F

from telegram import Update

from .models import MountInstance, ShareLink, User, File, Folder
from .forms import FileForm, FolderForm, ShareLinkForm
from .permissions import CheckFolderPermission, CheckFilePermission


@handler_decor()
def start(bot: TG_DJ_Bot, update: Update, user: User):
    self_root_folder = Folder.objects.filter(
        user_id=user.pk,
        parent_id__isnull=True
    ).first()

    if update.message and update.message.text.startswith('/start') and \
            len(update.message.text) > 6:
        share_code = update.message.text.split()[-1]
        share_link = ShareLink.objects.annotate(
            mounted_amount=Count('mountinstance')
        ).filter(
            share_code=share_code,
            mounted_amount__lt=F("share_amount")
        ).first()
        
        if share_link:
            MountInstance.objects.get_or_create(
                user=user,
                share_content=share_link,
                defaults={'mount_folder': self_root_folder}
            )

    fvs = FolderViewSet(telega_reverse('base:FolderViewSet'), user=user)
    __, (message, buttons) = fvs.show_list(self_root_folder.id)

    buttons.append([
        InlineKeyboardButtonDJ(_('⚙️ Settings'), callback_data='us/se')
    ])
    return bot.edit_or_send(update, message, buttons)


class FolderViewSet(TelegaViewSet):
    telega_form = FolderForm
    queryset = Folder.objects.all()
    viewset_name = gettext_lazy('Folder')
    updating_fields = ['name']
    permission_classes = [CheckFolderPermission]

    icon_format = {
        MESSAGE_FORMAT.TEXT: '📜',
        MESSAGE_FORMAT.PHOTO: '📷',
        MESSAGE_FORMAT.DOCUMENT: '📋',
        MESSAGE_FORMAT.AUDIO: '🔊',
        MESSAGE_FORMAT.VIDEO: '🎥',
        MESSAGE_FORMAT.GIF: '📺',
        MESSAGE_FORMAT.VOICE: '🗣',
        MESSAGE_FORMAT.VIDEO_NOTE: '🎬',
        MESSAGE_FORMAT.STICKER: '🎃',
        MESSAGE_FORMAT.LOCATION: '🗺',
        MESSAGE_FORMAT.GROUP_MEDIA: '📽'
    }

    def get_pretty_model_name(self, model, is_linked=False):
        name = ''
        if is_linked:
            name = '🔗'

        if isinstance(model, Folder):
            name += _('📁 %(model_name)s') % {'model_name': model.name}
        else:  # then File
            name += _(
                '%(icon)s  %(model_text)'
            ) % {
                'icon': self.icon_format[model.message_format],
                'model_text': model.text if model.text else model.message_format
            }
        return name

    def delete(self, model_or_pk, is_confirmed=False):
        model = self._get_elem(model_or_pk)

        if model:
            __, (mess, buttons) = super().delete(model_or_pk, is_confirmed)
            buttons = buttons[:-1]
            buttons.append([
                InlineKeyboardButtonDJ(
                    text=_('🔙 Return to folder'),
                    callback_data=self.gm_callback_data('show_list', model.parent.id)
                )
            ])
            return self.CHAT_ACTION_MESSAGE, (mess, buttons)
        else:
            return self.generate_message_no_elem(model_or_pk)

    def create(self, field=None, value=None):
        if field is None and value is None:
            self.user.clear_status(commit=False)

        initial_data = {}
        if field == 'parent' and value:
            initial_data = {'user': Folder.objects.get(id=value).user_id}  # created folder in folder is owned by same person as folder

        return self.create_or_update_helper(field, value, 'create', initial_data=initial_data)

    def show_elem(self, model_or_pk, mess=''):
        model = self._get_elem(model_or_pk)
        off = _('OFF')
        on = _('ON')

        if model:
            mess += _(
                'Folder: %(name)s\n'
                'Subfolder: %(subfolder_amount)s\n'
                'Files: %(files_amount)s\n'
                'General access: %(shared)s\n'
                'Changed: %(dttm)s\n'
            ) % {
                'name': model.name,
                'subfolder_amount': self.get_queryset().filter(parent_id=model.pk).count(),
                'files_amount': File.objects.filter(folder_id=model.pk).count(),
                'shared': on if ShareLink.objects.filter(folder_id=model.pk).count() else off,
                'dttm': model.last_modified.strftime("%d.%m.%Y %H:%M"),
            }

            button_lambda = lambda name, callback: [InlineKeyboardButtonDJ(text=name, callback_data=callback)]
            slvs = ShareLinkViewSet(telega_reverse('base:ShareLinkViewSet'))

            buttons = [
                button_lambda(_('📝 Title'), self.gm_callback_data('change', model.pk, 'name')),
            ]

            if model.parent_id:
                if self.user.id == model.user_id:
                    buttons.append(button_lambda(_('🔗 General access'), slvs.gm_callback_data('show_list', model.pk,'')))
                buttons.append(button_lambda(_('❌ Delete'), self.gm_callback_data('delete', model.pk)))

            buttons.append(button_lambda(_('🔙 Back'), self.gm_callback_data('show_list', model.pk)))

            return self.CHAT_ACTION_MESSAGE, (mess, buttons)
        else:
            return self.generate_message_no_elem(model)

    def show_list(self, folder_id, page=0, per_page=5, columns=1):
        """show list items"""

        current_folder = self._get_elem(folder_id)
        file_queryset = list(File.objects.filter(folder_id=folder_id))
        subfolder_queryset = list(self.get_queryset().filter(parent_id=folder_id))

        share_queryset = list(MountInstance.objects.filter(
            user_id=self.user.id,
            mount_folder=folder_id
        ).select_related('share_content', 'share_content__folder',  'share_content__file'))

        count_subfolder = len(subfolder_queryset)
        count_file = len(file_queryset)
        count_share = len(share_queryset)

        mess = ''
        buttons = []
        page = int(page)
        
        first_this_page = page * per_page * columns
        first_next_page = (page + 1) * per_page * columns

        models = (subfolder_queryset + file_queryset + share_queryset)[first_this_page: first_next_page]
        count_models = count_subfolder + count_file + count_share

        prev_page_button = InlineKeyboardButtonDJ(
            text=_(f'◀️️️'),
            callback_data=self.generate_message_callback_data(
                self.command_routings['command_routing_show_list'],
                folder_id,
                str(page - 1)
            )
        )
        next_page_button = InlineKeyboardButtonDJ(
            text=_(f'▶️️'),
            callback_data=self.generate_message_callback_data(
                self.command_routings['command_routing_show_list'],
                folder_id,
                str(page + 1)
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

        mess += _(
            'Folder: %(folder_name)s\n'
            'Subfolder: %(count_subfolder)d\n'
            'Files: %(count_file)d\n'
            'Added files: %(count_share)d\n'
            'Changed: %(date_change)s'
        ) % {
            'folder_name': current_folder.name,
            'count_subfolder': count_subfolder,
            'count_file': count_file,
            'count_share': count_share,
            'date_change': current_folder.last_modified.strftime("%d.%m.%Y %H:%M")
        }

        # static buttons for changes creating
        if self.user.id == current_folder.user_id:

            has_change_permission = True
        else:
            has_change_permission = ShareLink.objects.filter(
                mountinstance__user=self.user,
                type_link=ShareLink.TYPE_SHOW_CHANGE,
                folder__in=current_folder.get_ancestors(include_self=True)
            ).count()

        if has_change_permission:
            if current_folder.parent_id:
                buttons.append([
                    InlineKeyboardButtonDJ(
                        text=_('📝 Edit %(name)s') % {'name': current_folder.name},
                        callback_data=self.gm_callback_data(
                            'show_elem', current_folder.pk
                        )
                    )
                ])

            buttons += [
                [
                    InlineKeyboardButtonDJ(
                        text=_('➕ Add folder'),
                        callback_data=self.gm_callback_data(
                            'create', 'parent', current_folder.pk
                        )
                    ),
                    InlineKeyboardButtonDJ(
                        text=_('➕ Add file'),
                        callback_data=FileViewSet(
                            telega_reverse('base:FileViewSet')
                        ).gm_callback_data('create', 'folder', current_folder.pk)
                    )
                ]
            ]

        # return button
        if current_folder.parent_id:
            mount_curr_folder_query = MountInstance.objects.filter(share_content__folder_id=current_folder.id, user=self.user)
            if self.user.id != current_folder.user_id and (mount_inst := mount_curr_folder_query.first()):
                return_show_folder_id = mount_inst.mount_folder_id
            else:
                return_show_folder_id = current_folder.parent_id

            buttons.append([
                InlineKeyboardButtonDJ(
                    text=_('🔙 Back'),
                    callback_data=self.gm_callback_data('show_list', return_show_folder_id)
                )
            ])

        # buttons for folder, files and mount instances
        fvs = FileViewSet(telega_reverse('base:FileViewSet'))
        for it_m, model in enumerate(models, page * per_page * columns + 1):
            is_linked = False
            if isinstance(model, MountInstance):
                is_linked = True
                model = model.share_content.file or model.share_content.folder

            if isinstance(model, Folder):
                button_callback_data = self.gm_callback_data('show_list', model.pk)
            else:
                button_callback_data = fvs.gm_callback_data('show_elem', model.pk)

            buttons.append([
                InlineKeyboardButtonDJ(
                    text=self.get_pretty_model_name(model, is_linked),
                    callback_data=button_callback_data,
                )
            ])

        return self.CHAT_ACTION_MESSAGE, (mess, buttons)

    # def generate_message_self_variant(
    #     self, field_name, mess='', func_response='create',instance_id=None):
    #     __, (message, buttons) = super().generate_message_self_variant(
    #         field_name, str(mess), func_response, instance_id
    #     )
    #
    #     if field_name == 'name':
    #         mess += _(
    #             'Введите название папки 📁'
    #         )
    #     else:
    #         mess = message
    #
    #     return self.CHAT_ACTION_MESSAGE, (mess, buttons)


class FileViewSet(TelegaViewSet):
    telega_form = FileForm
    queryset = File.objects.all()
    viewset_name = gettext_lazy('File')
    updating_fields = ['text', 'media_id']
    actions = ['create', 'change', 'delete', 'show_elem']
    permission_classes = [CheckFilePermission]

    def create(self, field=None, value=None):
        if field is None and value is None:
            self.user.clear_status(commit=False)

        initial_data = {}
        if field == 'folder' and value:
            initial_data = {'user': Folder.objects.get(id=value).user_id}  # created file in folder is owned by same person as folder

        return self.create_or_update_helper(field, value, 'create', initial_data=initial_data)

    def create_or_update_helper(self, field, value, func_response='create', instance=None, initial_data=None):

        initial_data = {} if initial_data is None else copy.deepcopy(initial_data)

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

        return super().create_or_update_helper(field, value, func_response, instance, initial_data)

    def generate_message_self_variant(self, field_name, mess='', func_response='create', instance_id=None):
        __, (message, buttons) = super().generate_message_self_variant(field_name, str(mess), func_response,instance_id)

        if field_name == 'media_id':
            mess += _('Please send the file you want to keep (you can send it in a message) 🗄')
        else:
            mess = message

        return self.CHAT_ACTION_MESSAGE, (mess, buttons)

    def delete(self, model_or_pk, is_confirmed=False):
        model = self._get_elem(model_or_pk)

        if model:
            __, (mess, buttons) = super().delete(model_or_pk, is_confirmed)
            buttons = buttons[:-1]
            buttons.append([
                InlineKeyboardButtonDJ(
                    text=_('🔙 Back'),
                    callback_data=FolderViewSet(telega_reverse('base:FolderViewSet')).gm_callback_data(
                        'show_list', model.folder.pk
                    )
                )
            ])
            return self.CHAT_ACTION_MESSAGE, (mess, buttons)
        else:
            return self.generate_message_no_elem(model_or_pk)

    def generate_elem_buttons(self, model, elem_per_raw=2):
        buttons = []

        button_lambda = lambda name, callback: [InlineKeyboardButtonDJ(text=name, callback_data=callback)]
        fvs = FolderViewSet(telega_reverse('base:FolderViewSet'))
        slvs = ShareLinkViewSet(telega_reverse('base:ShareLinkViewSet'))

        if self.user.id == model.user_id:
            has_change_permission = True
        else:
            share_queryset = ShareLink.objects.filter(
                mountinstance__user=self.user,
                type_link=ShareLink.TYPE_SHOW_CHANGE,
            )

            has_change_permission = share_queryset.filter(file_id=model.id).count()
            if not has_change_permission:
                has_change_permission = share_queryset.filter(
                    folder_id__in= model.folder.get_ancestors(include_self=True)
                ).count()


        if has_change_permission:
            buttons += [
                button_lambda(_('🗄 File'), self.gm_callback_data('change', model.id, 'media_id')),
                button_lambda(_('💬 Note'), self.gm_callback_data('change', model.id, 'text')),
            ]

            if self.user.id == model.user_id:
                buttons.append(button_lambda(_('🔗 General access'), slvs.gm_callback_data('show_list', '', model.id)))

            buttons.append(button_lambda(_('❌ Delete'), self.gm_callback_data('delete', model.id)))

        mount_curr_folder_query = MountInstance.objects.filter(share_content__file_id=model.id, user=self.user)

        if self.user.id != model.user_id and (mount_inst := mount_curr_folder_query.first()):
            return_show_folder_id = mount_inst.mount_folder_id
        else:
            return_show_folder_id = model.folder_id

        buttons.append(button_lambda(_('🔙 Back'), fvs.gm_callback_data('show_list', return_show_folder_id)))

        return buttons

    def show_elem(self, model_or_pk, mess=''):
        model = self._get_elem(model_or_pk)

        if model:
            buttons = self.generate_elem_buttons(model)
            send_kwargs = {
                'text': model.text,
                'media_files_list': [model.media_id],
                'update': self.update,
                'reply_markup': InlineKeyboardMarkupDJ(buttons)
            }
            return model.message_format, send_kwargs
        else:
            return self.generate_message_no_elem(model_or_pk)

    def send_answer(self, chat_action, chat_action_args, utrl, user, *args, **kwargs):
        if chat_action in list(map(lambda x: x[0], MESSAGE_FORMAT.MESSAGE_FORMATS)):
            return self.bot.send_format_message(
                message_format=chat_action,
                **chat_action_args,
            )
        else:
            return super().send_answer(chat_action, chat_action_args, utrl, user, *args, **kwargs)


class ShareLinkViewSet(TelegaViewSet):
    telega_form = ShareLinkForm
    queryset = ShareLink.objects.all()
    viewset_name = _('Share')
    updating_fields = ['type_link', 'share_amount']
    foreign_filter_amount = 2  # [folder_id, file_id], only one field should be filled (if 2, then the first one used)

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.foreign_filters[0]:
            return queryset.filter(folder=self.foreign_filters[0], folder__user_id=self.user.id)
        else:
            return queryset.filter(file=self.foreign_filters[1], file__user_id=self.user.id)

    def create(self, field=None, value=None):
        
        if field is None and value is None:
            self.user.clear_status(commit=False)

        initial_data = {
            'share_code': str(uuid4()),
        }

        if self.foreign_filters[0]:
            initial_data['file'] = ''
            initial_data['folder'] = self.foreign_filters[0]

        else:
            initial_data['file'] = self.foreign_filters[1]
            initial_data['folder'] = ''

        return self.create_or_update_helper(field, value, 'create', initial_data=initial_data)

    def generate_show_fields(self, model, full_show=False):
        mess = super().generate_show_fields(model, full_show)
        mess += f'https://t.me/{settings.MAIN_BOT_USERNAME}?start={model.share_code}'
        return mess

    def show_list(self, page=0, per_page=10, columns=1):
        __, (mess, buttons) = super().show_list(page, per_page, columns)

        button_lambda = lambda name, callback: [InlineKeyboardButtonDJ(text=name, callback_data=callback)]

        if self.foreign_filters[0]:
            return_button_callback = FolderViewSet(telega_reverse('base:FolderViewSet')).gm_callback_data(
                'show_elem', self.foreign_filters[0]
            )
        else:
            return_button_callback = FileViewSet(telega_reverse('base:FileViewSet')).gm_callback_data(
                'show_elem', self.foreign_filters[1]
            )

        print(f'return_button_callback {return_button_callback}')

        buttons += [
            button_lambda(_('➕ Add'), self.gm_callback_data('create')),
            button_lambda(_('🔙 Back'), return_button_callback),
        ]

        return self.CHAT_ACTION_MESSAGE, (mess, buttons)

    # def generate_elem_buttons(self, model, elem_per_raw=2):
    #     buttons = []
    #
    #     if model.folder:
    #         buttons += [
    #             [
    #                 InlineKeyboardButtonDJ(
    #                     text=_('🔙 Назад в папку'),
    #                     callback_data=FolderViewSet(
    #                         telega_reverse('base:FolderViewSet')
    #                     ).gm_callback_data('show_elem', model.folder.id)
    #                 ),
    #             ]
    #         ]
    #     elif model.file:
    #         buttons += [
    #             [
    #                 InlineKeyboardButtonDJ(
    #                     text=_('🔙 Назад в файл'),
    #                     callback_data=FolderViewSet(
    #                         telega_reverse('base:FileViewSet')
    #                     ).gm_callback_data('show_elem', model.file.id)
    #                 ),
    #             ]
    #         ]
    #
    #     buttons += [
    #         [
    #             InlineKeyboardButtonDJ(
    #                 text=_('Type link'),
    #                 callback_data=self.gm_callback_data(
    #                     'change', model.id, 'type_link'
    #                 )
    #             ),
    #         ],
    #         [
    #             InlineKeyboardButtonDJ(
    #                 text=_('Share amount'),
    #                 callback_data=self.gm_callback_data(
    #                     'change', model.id, 'share_amount'
    #                 )
    #             ),
    #         ],
    #         [
    #             InlineKeyboardButtonDJ(
    #                 text=_('❌ Удалить'),
    #                 callback_data=self.gm_callback_data(
    #                     'delete', model.id
    #                 )
    #             ),
    #         ],
    #     ]
    #
    #     return buttons
