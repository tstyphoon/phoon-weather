"""入口：載入設定與所有功能，啟動 bot。

四段防護在程式裡的位置（以搜尋「防護 N 開始」為準，行號會隨修改移動）：
  防護 1  core/claude.py     claude -p 的檔案範圍隔離
  防護 2  core/claude.py     使用者文字只當資料
  防護 3  core/pipeline.py   模型回來的名稱拿去當檔名前先清洗
  防護 4  core/pipeline.py   寫進紀錄與顯示的文字清洗
"""
import logging
import sys

from core.bot import WeatherBot
from core.claude import ClaudeRunner
from core.config import ConfigError, load_config
from core.registry import RegistryError, load_plugins
from core.store import Store
from services.weather import WeatherService


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        config = load_config()
        load_plugins()
    except (ConfigError, RegistryError) as e:
        print(f"啟動失敗：{e}", file=sys.stderr)
        return 1

    store = Store(config.db_path, config.images_dir)
    weather = WeatherService(config.cwa_api_key)
    claude = ClaudeRunner(config.claude_model)
    bot = WeatherBot(config, store, weather, claude)
    bot.run(config.discord_token, log_handler=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
