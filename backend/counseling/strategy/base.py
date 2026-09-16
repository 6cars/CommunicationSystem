class BaseDialogueStrategy:
    """対話戦略エンジンの基本クラス。アルゴリズム実装は具象クラスで差し替える。"""

    def get_initial_messages(self, session=None, user_name: str = "") -> list[str]:
        display_name = user_name or "ゲスト"
        return [
            f"{display_name}さん，今日はよろしくお願いします．",
            "あなたはどんな失敗をしたんですか？ここでお話しいただく内容はすべて安心して、あなたのペースで構いませんので、今心に引っかかっていることや、モヤモヤしていることを何でもお聞かせくださいね．",
            "あなたは、失敗した時どのような行動をとってしまいましたか？",
        ]

    def get_initial_message(self, session=None, user_name: str = "") -> str:
        return "\n\n".join(self.get_initial_messages(session, user_name=user_name))

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
