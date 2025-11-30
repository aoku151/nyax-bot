header = {"Content-Type": "application/json"}

dmCommandList = [
    "/hello",
    "/help"
]

dmCommands = ""
if len(dmCommandList) != 0:
    for i in dmCommandList:
        dmCommands += f"{i}\n"

dmInviteMessage = f"""\
NyaXBotへのDMが開通しました! _veryx2-long-cat_
開発者: @4332
Githubリポジトリ: https://github.com/aoku151/nyax-bot/

使用出来るコマンド
{dmCommands}"""

helpMessage = f"""\
NyaXBot @1340
開発者: @4332
Githubリポジトリ: https://github.com/aoku151/nyax-bot/

使用できるコマンド
{dmCommands}"""
