# -*- coding: utf-8 -*-
# 本地配置的读写（Windows 注册表）与登录凭据的维护
#
# 鉴权相关三项：
# - access_token：X-ND-AUTH 的 MAC id，也用于 Authorization: Bearer
# - mac_key：官网 HMAC 密钥；没有它就只能生成占位头
# - token_diff：官网 Fe(diff) 的时钟差（毫秒），只影响 nonce 时间戳
# 不要把 refresh_token 写入配置。旧用户可能只有 AccessToken 注册表值，加载时 mac_key 为空是正常的。

from __future__ import annotations

import winreg

from .auth import TokenCredentials, parse_token_input
from .network import headers
from .platform_utils import print_error

access_token: str | None = None
mac_key: str | None = None
token_diff: int = 0 # 与 UC Token JSON 的 diff 对应，单位毫秒

REGISTRY_PATH = "Software\\tchMaterial-parser-for-Windows7" # 存放配置的注册表键
CONFIG_KEYS = { # 配置项名称到注册表值名称的映射
    "access_token": "AccessToken",
    "mac_key": "MacKey",
    "token_diff": "TokenDiff",
    "theme": "Theme",
}

def config_location() -> str: # 获取配置存放位置的描述文本，用于提示用户
    return f"已写入注册表：HKEY_CURRENT_USER\\{REGISTRY_PATH}"

def load_config() -> dict[str, str]: # 从注册表读取本地配置
    config: dict[str, str] = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ) as key:
            for name, value_name in CONFIG_KEYS.items():
                try:
                    value, _ = winreg.QueryValueEx(key, value_name)
                except FileNotFoundError: # 该配置项尚未写入
                    continue
                if not isinstance(value, str):
                    print_error(TypeError(f"配置项 {name} 必须是字符串"))
                    continue
                config[name] = value
    except FileNotFoundError: # 注册表键不存在，即从未保存过配置
        return {}
    except Exception as e:
        print_error(e)
        return {}

    return config

def save_config(**updates: str) -> None: # 保存配置，并与已有配置合并
    # 注册表以单个值（而非整个键）为单位写入，因此未被本次更新的配置项会自动保留
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
        for name, value in updates.items():
            winreg.SetValueEx(key, CONFIG_KEYS[name], 0, winreg.REG_SZ, value)

def apply_static_headers() -> None:
    """更新全局占位头。私有下载不要用这份 X-ND-AUTH，应走 network.request_headers。"""
    headers["Authorization"] = f"Bearer {access_token or '0'}"
    headers["X-ND-AUTH"] = f'MAC id="{access_token or "0"}",nonce="0",mac="0"'

def apply_credentials(credentials: TokenCredentials) -> None:
    """写入内存中的凭据并刷新占位头。空 access_token 视为未登录。"""
    global access_token, mac_key, token_diff
    access_token = credentials.access_token or None
    mac_key = credentials.mac_key
    token_diff = credentials.diff
    apply_static_headers()

def load_access_token(config: dict[str, str]) -> None: # 从已读取的配置中加载登录凭据
    token = config.get("access_token") or ""
    stored_mac = config.get("mac_key") or ""
    try:
        stored_diff = int(config.get("token_diff") or 0)
    except ValueError:
        stored_diff = 0
    apply_credentials(TokenCredentials(token, stored_mac or None, stored_diff))

def set_access_token(raw: str) -> str: # 校验三项 JSON 并保存；空内容则清除已保存的登录凭据
    credentials = parse_token_input(raw)
    apply_credentials(credentials)
    save_config(
        access_token=credentials.access_token,
        mac_key=credentials.mac_key or "",
        token_diff=str(credentials.diff),
    )
    if not credentials.access_token:
        return f"登录凭据已清除。\n{config_location()}"
    return f"登录凭据已保存！\n{config_location()}"
