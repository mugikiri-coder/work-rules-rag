import os, sys
from dotenv import load_dotenv

REQUIRED = [
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_EMBED_DEPLOYMENT",
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_ADMIN_KEY",
    "AZURE_SEARCH_INDEX",
    "AZURE_SEARCH_API_VERSION",
    "EMBED_DIM",
]

def main():
    # .env があれば読む（無ければ example の存在だけ確認）
    if os.path.exists(".env"):
        load_dotenv(".env")
        env_loaded = ".env"
    else:
        env_loaded = "(no .env; using process env only)"

    missing = []
    issues = []

    for k in REQUIRED:
        v = os.getenv(k, "").strip()
        if not v:
            missing.append(k)

    # 追加バリデーション
    api_ver = os.getenv("AZURE_SEARCH_API_VERSION", "")
    if api_ver and not api_ver.startswith("2024-"):
        issues.append(f"AZURE_SEARCH_API_VERSION looks unusual: {api_ver}")

    dim = os.getenv("EMBED_DIM", "")
    if dim:
        try:
            dim_i = int(dim)
            if dim_i not in (1536, 3072):
                issues.append(f"EMBED_DIM should be 1536 or 3072; got {dim_i}")
        except ValueError:
            issues.append(f"EMBED_DIM is not an integer: {dim}")

    print(f"[env] loaded: {env_loaded}")
    if os.path.exists(".env.example"):
        print("[hint] .env.example found (use: copy to .env and fill values)")

    if missing:
        print("\n[missing] required keys not set:")
        for k in missing:
            print("  -", k)
    else:
        print("\n[ok] all required keys are present")

    if issues:
        print("\n[notes] please review:")
        for m in issues:
            print("  -", m)

    # exit code: 0=OK(全部埋まってる), 1=不足あり
    sys.exit(0 if not missing else 1)

if __name__ == "__main__":
    main()
