from django.utils.module_loading import import_string

from counseling.strategy.base import BaseDialogueStrategy


def load_strategy() -> BaseDialogueStrategy:
    from django.conf import settings

    class_path = settings.DIALOGUE_STRATEGY_CLASS
    strategy_cls = import_string(class_path)
    return strategy_cls()
