# sosovalue
1.基于morelogin环境的sosovalue项目的每日签到任务,包含每日任务和新手礼包，支持中文简体、中文繁体和英文。
2.支持稳定的morelogin环境的登录状态，钱包已绑定，页面可以直接显示exp积分的；
3.需要morelogin的参数如下：
appid = os.getenv("APPID") 详见morelogin的API
secretkey = os.getenv("SECRETKEY") 详见morelogin的API
encryptkey = os.getenv("ENCRYPTKEY") 环境端对端加密密钥
baseurl = os.getenv("BASEURL") 详见morelogin的API
4.JSON文件格式
[
  {
    "env_name": "TW004-02",
    "env_id": "1943610540078735360",
    "url": "https://sosovalue.com",
    "tag": "okx"
  }
  .....
]

USSI的购买和质押
1.多钱包格式
[{
        "address": evm_address,
        "private_key": private_key,
        "public_key": public_key
    }
    ]
2.代码中的私钥是从sqlite获取助记词再生成的，若实际使用按上述json文件格式构造好钱包地址、私钥、公钥数据即可。
