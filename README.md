
### 代码部署

```bash
# 进入到代码目录
cd auto_kite
# 创建虚拟环境
python -m venv venv
# 激活虚拟环境
source venv/bin/activate
# 在虚拟环境中安装依赖包
pip install -r requirements.txt
# 拷贝默认配置
cp conf.py.sample conf.py
cp datas/purse/purse.csv.sample datas/purse/purse.csv
```

### Run
```bash
python kite.py --url=https://testnet.gokite.ai/ --manual_exit --profile=g01
```
