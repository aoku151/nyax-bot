header = {"Content-Type": "application/json"}

dmCommandList = []

dmCommands = ""
if len(dmCommandList) != 0:
    dmCommands += f"{i}\n"

dmInviteMessage = f"""\
NyaXBotへのDMが開通しました! _veryx2-long-cat_
開発者: @4332
Githubリポジトリ: https://github.com/aoku151/nyax-bot/

使用出来るコマンド
{dmCommands}
"""
