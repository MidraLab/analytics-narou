import requests
import csv
import gzip
import io
import yaml

# APIエンドポイント
api_url = 'https://api.syosetu.com/novelapi/api/'

# データを格納するリスト
data = []

# 最小文字数と最大文字数を設定（1時間以上3時間未満の読了時間に相当）
minlen = 30000    # 30,000文字（1時間）
maxlen = 89500000    # 89,500文字（179分相当。180分未満とするため）

# APIから取得できる最大件数は500件なので、stパラメータを使用して複数回に分けて取得します
# 総合ポイントでの直接フィルタリングはできないため、order=hyokaでソートし上位からデータを取得します
# 必要に応じてstを増やし、データ件数を増やすことができます（stの最大値は2000）
for st in range(1, 2001, 500):
    # GETパラメータを準備
    params = {
        'order': 'hyoka',        # 総合ポイントの高い順にソート
        'lim': '500',            # 最大500件取得
        'st': str(st),           # 表示開始位置
        'minlen': str(minlen),   # 最小文字数を指定
        'maxlen': str(maxlen),   # 最大文字数を指定
        'out': 'yaml',           # 出力形式をYAMLに指定
        'gzip': '5',             # 転送量を削減するためにgzip圧縮を利用
        'of': 't-n-l-gp-k',      # 出力項目：タイトル、Nコード、文字数、総合ポイント、キーワード
    }

    # APIリクエストを送信
    response = requests.get(api_url, params=params)

    # レスポンスのステータスを確認
    if response.status_code != 200:
        print(f"データ取得中にエラーが発生しました。ステータスコード：{response.status_code}")
        continue

    # gzip圧縮された内容を解凍
    compressed_data = io.BytesIO(response.content)
    with gzip.GzipFile(fileobj=compressed_data) as f:
        decompressed_data = f.read()

    # YAMLレスポンスを解析
    try:
        novels = yaml.safe_load(decompressed_data)
    except yaml.YAMLError:
        print("YAML解析中にエラーが発生しました。")
        continue

    # 小説が見つかったか確認
    if not novels or len(novels) < 2:
        print("該当する小説が見つかりませんでした。")
        continue

    # データの重複を防ぐためにNコードを格納するセットを使用
    ncode_set = set()

    # 取得した小説をループ処理
    for novel_info in novels[1:]:
        ncode = novel_info.get('ncode', '').lower()

        # 重複チェック
        if ncode in ncode_set:
            continue
        ncode_set.add(ncode)

        global_point = novel_info.get('global_point', 0)

        # 総合ポイントが10万以上の小説をフィルタリング
        if global_point >= 100000:
            title = novel_info.get('title', '')
            length = novel_info.get('length', '')
            keywords = novel_info.get('keyword', '')
            time = -(-length // 500)  # 読了時間を計算（切り上げ）

            # データをリストに追加
            data.append({
                'タイトル': title,
                'キーワード': keywords,
                '総合ポイント': global_point,
                '文字数': length,
                '読了時間（分）': time,
                'URL': f'https://ncode.syosetu.com/{ncode}/',
            })

# CSVファイルのフィールド名を定義
fieldnames = ['タイトル', 'キーワード', '総合ポイント', '文字数', '読了時間（分）', 'URL']

# データをCSVファイルに書き込む
with open('novel_data.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)

print("データがnovel_data.csvに書き込まれました。")