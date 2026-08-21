class BaseDialogueStrategy:
    """対話戦略エンジンの基本クラス。アルゴリズム実装は具象クラスで差し替える。"""

    INITIAL_MESSAGE = "こんにちは。今日はお話ししたいことがあれば何でも教えてくださいね。"

    def get_initial_message(self) -> str:
        return self.INITIAL_MESSAGE

    def process_turn(self, session, user_message: str) -> dict:
        """
        引数:
            session: CounselingSession インスタンス (現在の状態)
            user_message: str (ユーザー入力文字列)
        戻り値:
            dict: {
                "reply_text": str,          # エージェントの応答文
                "next_phase": str,          # 更新後の対話フェーズ
                "state_updates": dict,      # 保存すべき内部状態
                "strategy_metadata": dict   # ログ用メタデータ
            }
        """
        raise NotImplementedError
