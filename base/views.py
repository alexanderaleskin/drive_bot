import copy
from uuid import uuid4
import logging

from django.conf import settings

from telegram_django_bot.models import MESSAGE_FORMAT, ActionLog
from telegram_django_bot.routing import telega_reverse
from telegram_django_bot.telegram_lib_redefinition import InlineKeyboardButtonDJ, InlineKeyboardMarkupDJ
from telegram_django_bot.td_viewset import TelegaViewSet
from telegram_django_bot.utils import handler_decor
from telegram_django_bot.tg_dj_bot import TG_DJ_Bot

from django.utils import timezone
from django.utils.translation import gettext as _, gettext_lazy
from django.db.models import Count, F

from telegram import Update

from .models import MountInstance, ShareLink, User, File, Folder
from .forms import FileForm, FolderForm, ShareLinkForm
from .permissions import CheckFolderPermission, CheckFilePermission


@handler_decor()
def create_file_from_message(bot: TG_DJ_Bot, update: Update, user: User):
    root_folder = Folder.objects.get(
        user_id=user.id,
        parent__isnull=True
    )
    
    fl = FileViewSet(telega_reverse('base:FileViewSet'), update=update, user=user, bot=bot)
    fl.create('folder', root_folder.pk)
    fl.create('media_id', '')

    fvs = FolderViewSet(telega_reverse('base:FolderViewSet'), user=user)
    __, (message, buttons) = fvs.show_list(root_folder.pk)

    return bot.edit_or_send(update, message, buttons)


@handler_decor()
def select_folder(bot: TG_DJ_Bot, update: Update, user: User):
    select_folder_pk = int(update.callback_query['data'].split('/')[1])
    select_folder = Folder.objects.filter(pk=select_folder_pk).first()

    context = user.current_utrl_context
    portable_is_folder = context['model_type'] == 'Folder'

    ModelORM = Folder if portable_is_folder else File
    portable_instance = ModelORM.objects.filter(pk=context['model_pk']).first()
    mount_instance = None

    has_change_location_permission = True
    if portable_instance.user_id != user.id or select_folder.user_id != user.id:
        # some instance is not ownered by user and we need more checks

        if select_folder.user_id != user.id:
            # check if user has permission for change folder
            exist_sharelink = ShareLink.objects.filter(
                type_link=ShareLink.TYPE_SHOW_CHANGE,
                mountinstance__user_id=user.id,
                folder_id__in=select_folder.get_ancestors(include_self=True)
            )

            if exist_sharelink.count() == 0:
                has_change_location_permission = False

        if has_change_location_permission and portable_instance.user_id != user.id:
            # special restriction: could transfer only:
            # from self tree to someone tree or from someone tree to self or change in someone tree
            # could not transfer from someone tree to someone else's tree
            if not select_folder.user_id in [user.id, portable_instance.user_id]:
                has_change_location_permission = False

            else:
                if portable_is_folder:
                    check_folders = portable_instance.get_ancestors(include_self=False)
                    mount_kwarg = {'share_content__folder_id': portable_instance.id}
                else:
                    check_folders = portable_instance.folder.get_ancestors(include_self=True)
                    mount_kwarg = {'share_content__file_id': portable_instance.id}

                mount_instance = MountInstance.objects.filter(user=user, **mount_kwarg).first()

                if mount_instance:
                    # actually only want change mount instance, not folder or file folder
                    # check that want mount only to self tree
                    if select_folder.user_id != user.id:
                        has_change_location_permission = False
                else:
                    # change folder or file folder, need check permissions
                    exist_sharelink = ShareLink.objects.filter(
                        type_link=ShareLink.TYPE_SHOW_CHANGE,
                        mountinstance__user_id=user.id,
                        folder_id__in=check_folders
                    )

                    if exist_sharelink.count() == 0:
                        has_change_location_permission = False

    if has_change_location_permission and portable_is_folder:
        # need extra check if there is no circle in the tree

        ancestors = select_folder.get_ancestors(include_self=True)
        if portable_instance.user_id == select_folder.user_id:
            exist_circle = portable_instance in ancestors
        else:
            mount_folder_instance = MountInstance.objects.filter(user=user, share_content__folder__in=ancestors).first()
            exist_circle = mount_folder_instance and \
                           portable_instance in mount_folder_instance.mount_folder.get_ancestors(include_self=True)

        has_change_location_permission = not exist_circle


    if has_change_location_permission:
        if mount_instance:
            mount_instance.mount_folder_id = select_folder.id
            mount_instance.save()
        elif portable_is_folder:
            portable_instance.parent_id = select_folder.id
            portable_instance.save()

            if portable_instance.user_id != select_folder.user_id:
                descendants = list(portable_instance.get_descendants(include_self=True).values_list('id', flat=True))
                Folder.objects.filter(id__in=descendants).update(user_id=select_folder.user_id)
                File.objects.filter(folder_id__in=descendants).update(user_id=select_folder.user_id)

        else:
            portable_instance.folder_id = select_folder.id
            portable_instance.save()

        start_mess = ''
        user.current_utrl_code_dttm = None
        user.save_context_in_db({})  # there is save in
        # user.clear_status()

    else:
        start_mess = _(
            '<b>You do not have permission for change location for %(title)s to folder %(folder_title)s. </b>\n'
            '\n'
        ) % {
            'title': portable_instance.name,
            'folder_title': select_folder.name,
        }

    fvs = FolderViewSet(telega_reverse('base:FolderViewSet'), user=user)
    __, (message, buttons) = fvs.show_list(select_folder_pk)

    return bot.edit_or_send(update, start_mess + message, buttons)


@handler_decor()
def change_location(bot: TG_DJ_Bot, update: Update, user: User):
    self_root_folder = Folder.objects.filter(
        user_id=user.pk,
        parent_id__isnull=True
    ).first()
    model_pk, model_type = update.callback_query['data'].split('/')[1:]
    context = {
        'location_mode': True,
        'model_pk': int(model_pk),
        'model_type': model_type
    }
    user.save_context_in_db(context)
    user.current_utrl_code_dttm = timezone.now()
    user.save()

    fvs = FolderViewSet(telega_reverse('base:FolderViewSet'), user=user)
    __, (message, buttons) = fvs.show_list(self_root_folder.id)

    return bot.edit_or_send(update, message, buttons)


@handler_decor()
def start(bot: TG_DJ_Bot, update: Update, user: User):
    user.clear_status()
    self_root_folder = Folder.objects.filter(
        user_id=user.pk,
        parent_id__isnull=True
    ).first()

    if user.date_joined > (timezone.now() - timezone.timedelta(seconds=1)):
        message = _(
            'Hi! 🤖\n'
            '\n'
            'I will help you to store and manage data like Yandex disk or Google drive does it. '
            'Now, you could store your files in Telegram in different folders and shared it with others.\n'
            '\n'
            'Similar to self chat but more useful for work in team or store different content in different areas.\n'
            '\n'
            'Try it!'
            
        )
        bot.edit_or_send(update, message)

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

    def get_pretty_model_name(self, model, is_linked=False):
        name = ''
        if is_linked:
            name = '🔗'

        if isinstance(model, Folder):
            name += _('📁 %(model_name)s') % {'model_name': model.name}
        else:  # then File
            name += model.get_name()

        if getattr(model, 'shared_amount', 0):
            name = '🌍' + name
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

    def generate_show_fields(self, model, full_show=False, **kwargs):
        mess = _(
            '📂 Folder: %(folder_name)s\n'
            '\n'
            '<i>🗂 Subfolder: %(count_subfolder)d\n'
            '📑 Files: %(count_file)d\n'
            '🔗 Shared content: %(count_share)d\n'
            '🕑 Last change: %(date_change)s</i>\n'
        ) % {
            'folder_name': model.get_path(self.user.id),
            'count_subfolder': kwargs.get('count_subfolder', self.get_queryset().filter(parent_id=model.pk).count()),
            'count_file': kwargs.get('count_file', File.objects.filter(folder_id=model.pk).count()),
            'count_share': kwargs.get('count_share', MountInstance.objects.filter(mount_folder=model.id).count()),
            'date_change': model.last_modified.strftime("%d.%m.%Y %H:%M")
        }

        if full_show:
            mess += _(
                '\n'
                'Public folder: %(shared)s\n'
            ) % {
                'shared': _('🌍 Yes') if ShareLink.objects.filter(folder_id=model.pk).count() else _('🚫 No'),
            }

        return mess

    def show_elem(self, model_or_pk, mess=''):
        model = self._get_elem(model_or_pk)

        if model:

            mess += self.generate_show_fields(model, full_show=True)

            button_lambda = lambda name, callback: [InlineKeyboardButtonDJ(text=name, callback_data=callback)]
            slvs = ShareLinkViewSet(telega_reverse('base:ShareLinkViewSet'))

            buttons = [
                button_lambda(_('📝 Title'), self.gm_callback_data('change', model.pk, 'name')),
                button_lambda(_('🗺 Change location'), f'change_location/{model.pk}/Folder')
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
        mount_curr_folder_query = MountInstance.objects.filter(
            share_content__folder_id=current_folder.id,
            user=self.user
        ).first()
        context = self.user.current_utrl_context

        subfolder_queryset= list(
            self.get_queryset().filter(parent_id=folder_id).annotate(shared_amount=Count('sharelinks__id'))
        )
        share_queryset = MountInstance.objects.filter(
            user_id=self.user.id,
            mount_folder=folder_id
        ).select_related('share_content', 'share_content__folder',  'share_content__file')

        if context.get('location_mode'):
            time_start = self.user.current_utrl_code_dttm
            if (timezone.now() - time_start) > timezone.timedelta(seconds=3600):
                context = {}
                self.user.clear_status()
        
        if context.get('location_mode'):
            file_queryset = []
            share_queryset = list(share_queryset.filter(
                share_content__file__isnull=True
            ))   
        else:
            file_queryset = list(
                File.objects.filter(folder_id=folder_id).annotate(shared_amount=Count('sharelinks__id'))
            )
            share_queryset = list(share_queryset)

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
                logging.error(f'unreal situation {count_models}, \
                    {len(models)}, {first_this_page}, {first_next_page}')

        mess += self.generate_show_fields(current_folder)

        # static buttons for changes creating
        if self.user.id == current_folder.user_id:

            has_change_permission = True
        else:
            has_change_permission = ShareLink.objects.filter(
                mountinstance__user=self.user,
                type_link=ShareLink.TYPE_SHOW_CHANGE,
                folder__in=current_folder.get_ancestors(include_self=True)
            ).count()

        edit_button = InlineKeyboardButtonDJ(
            text=_('⚙️ %(name)s') % {'name': current_folder.name},
            callback_data=self.gm_callback_data(
                'show_elem', current_folder.pk
            )
        )
        if has_change_permission:
            if context.get('location_mode'):
                main_folder_name = _('Main')
                folder_name = current_folder.name if current_folder.parent_id else main_folder_name

                mess = _(
                    'To change the location, select a folder and click «Place in Folder»\n'
                    'Folder selected: %(name)s\n'
                ) % {
                    'name': folder_name
                }

                buttons += [
                    [
                        InlineKeyboardButtonDJ(
                            text=_('✔️ Place in a folder %(name)s') % {'name': folder_name},
                            callback_data=f'select_folder/{current_folder.pk}'
                        ),
                    ],
                    [
                        InlineKeyboardButtonDJ(
                            text=_('❌ Cancel'),
                            callback_data='start'
                        )
                    ]
                ]
            else:

                action_button_line = [
                    InlineKeyboardButtonDJ(
                        text=_('➕ Folder'),
                        callback_data=self.gm_callback_data(
                            'create', 'parent', current_folder.pk
                        )
                    ),
                    InlineKeyboardButtonDJ(
                        text=_('➕ File'),
                        callback_data=FileViewSet(
                            telega_reverse('base:FileViewSet')
                        ).gm_callback_data('create', 'folder', current_folder.pk)
                    ),
                ]

                if current_folder.parent_id:
                    action_button_line.append(edit_button)

                buttons.append(action_button_line)

        elif mount_curr_folder_query:
            # it is mount folder and we give opportunity for change location
            buttons.append([edit_button])

        # return button
        if current_folder.parent_id:
            # mount_curr_folder_query = MountInstance.objects.filter(share_content__folder_id=current_folder.id, user=self.user)
            if self.user.id != current_folder.user_id and (mount_inst := mount_curr_folder_query):
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
        items_buttons = []
        for it_m, model in enumerate(models, page * per_page * columns + 1):
            is_linked = False
            if isinstance(model, MountInstance):
                is_linked = True
                model = model.share_content.file or model.share_content.folder

            if isinstance(model, Folder):
                button_callback_data = self.gm_callback_data('show_list', model.pk)
            else:
                button_callback_data = fvs.gm_callback_data('show_elem', model.pk)

            items_buttons.append([
                InlineKeyboardButtonDJ(
                    text=self.get_pretty_model_name(model, is_linked),
                    callback_data=button_callback_data,
                )
            ])

        buttons = items_buttons + buttons

        return self.CHAT_ACTION_MESSAGE, (mess, buttons)


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
                    'name': message.document['file_name'],
                }
            elif message.document:
                initial_data = {
                    'message_format': MESSAGE_FORMAT.DOCUMENT,
                    'media_id': message.document['file_id'],
                    'name': message.document['file_name'],
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
                    'name': message.document['file_name'],
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
            mess += _('Please send the file or text(note) you want to keep (you can forward it also) 📇')
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
                    button_lambda(_('📇 Content'), self.gm_callback_data('change', model.id, 'media_id')) +
                    button_lambda(_('✏️ Name'), self.gm_callback_data('change', model.id, 'name')),
                button_lambda(_('💬 Text / Note'), self.gm_callback_data('change', model.id, 'text')),
                button_lambda(_('🗺 Change location'), f'change_location/{model.id}/File')
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
    viewset_name = _('Share access')
    updating_fields = ['type_link', 'share_amount']
    foreign_filter_amount = 2  # [folder_id, file_id], only one field should be filled (if 2, then the first one used)

    prechoice_fields_values = {
        'share_amount': (
            (1, '1'),
            (2, '2'),
            (5, '5'),
            (100000000, _('All')),
        )
    }

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
        mess = ''

        if model.folder:
            mess += _('📂 <b>Folder</b>: %(path)s\n') % {'path': model.folder.get_path(self.user.id)}
        else:
            mess += _('📇 <b>File</b>: %(name)s\n') % {'name': model.file.get_name()}

        mess += super().generate_show_fields(model, full_show)
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

        buttons += [
            button_lambda(_('➕ Add'), self.gm_callback_data('create')),
            button_lambda(_('🔙 Back'), return_button_callback),
        ]

        return self.CHAT_ACTION_MESSAGE, (mess, buttons)
