1. 运行下面的命令
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
2. flow 
- BuffAutoOnsale.py 自动售卖
  https://buff.163.com/api/market/steam_inventory  获取库存
  https://buff.163.com/api/market/goods/sell_order?goods_id=  获取售卖价格
  https://buff.163.com/api/market/sell_order/create/manual_plus 售卖
- BuffAutoAcceptOffer 自动接受报价
  https://buff.163.com/api/message/notification