from .models import ShareLink


class CheckFolderPermission:
    @staticmethod
    def check_type_for_change(model, share_link):
        if share_link.folder == model and \
                share_link.type_link == ShareLink.TYPE_SHOW_CHANGE:
            
            return True
        return False


class CheckFilePermission:
    @staticmethod
    def check_type_for_change(model, share_link):
        if share_link.file == model and \
                share_link.type_link == ShareLink.TYPE_SHOW_CHANGE:
            
            return True
        return False
