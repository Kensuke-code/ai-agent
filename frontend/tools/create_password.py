import sys
from streamlit_authenticator.utilities.hasher import Hasher


# 使い方
# $ docker compose exec frontend python ./tools/create_password.py "<平文のパスワード>"" で呼び出す

raw_password = sys.argv[1]
hashed_password = Hasher().hash(raw_password)
print('Hashed Password: ' + hashed_password)