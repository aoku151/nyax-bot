# まとめる必要がないヘッダー
header = {"Content-Type": "application/json"}

# DMで使えるコマンドのリスト
dmCommandList = [
    "/hello",
    "/help"
]

# 処理(変更禁止)
dmCommands = ""
if len(dmCommandList) != 0:
    for i in dmCommandList:
        dmCommands += f"{i}\n"

# DMに招待された時のメッセージ
dmInviteMessage = f"""\
NyaXBotへのDMが開通しました! _veryx2-long-cat_
開発者: @4332
Githubリポジトリ: https://github.com/aoku151/nyax-bot/

使用出来るコマンド
{dmCommands}"""

# Helpコマンドの応答
helpMessage = f"""\
NyaXBot @1340
開発者: @4332
Githubリポジトリ: https://github.com/aoku151/nyax-bot/

使用できるコマンド
{dmCommands}"""
