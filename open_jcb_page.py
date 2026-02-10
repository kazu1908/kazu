"""JCB THE CLASSページを別ウィンドウで開くスクリプト。"""

import webbrowser

URL = "https://www.jcb.co.jp/premium/theclass/"


def main() -> None:
    # new=1: 可能なら新しいウィンドウで開く
    opened = webbrowser.open(URL, new=1)
    if opened:
        print(f"Opened in a new window: {URL}")
    else:
        print(
            "ブラウザの起動に失敗しました。"
            "VSCodeでPythonインタープリタ設定を確認してください。"
        )


if __name__ == "__main__":
    main()
