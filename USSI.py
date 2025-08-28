import os
import requests
import json
import time
import random
from web3 import Web3
from eth_account import Account
from decimal import Decimal
from dotenv import load_dotenv
import sqlite3
from typing import List, Dict, Optional
from bip_utils import (
    Bip39MnemonicValidator, Bip39SeedGenerator,
    Bip44, Bip44Coins, Bip44Changes
)
from basefunc.item_logger_util import get_logger

#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = get_logger(__name__)
DB_PATH = r"D:\VSCODE\chromes\Itemdatabase.db"

class USSIBuyer:
    def __init__(self):
        # Base链配置
        self.chain_id = 8453
        self.rpc_url = "https://mainnet.base.org"  # Base官方RPC
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # 代币地址
        self.usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # Base USDC
        # 使用实际API调用中的USSI地址
        self.ussi_address = "0x3a46ed8fceb6ef1ada2e4600a522ae7e24d2ed18"  # 从实际API调用获取
        
        # LI.FI合约地址
        self.lifi_contract = "0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE"
        
        # 交易参数
        self.slippage = 0.005  # 0.5%滑点
        self.integrator = "sosovalue"
        
        # LI.FI API base URL (修复)
        self.base_url = "https://li.quest"
        
        # ERC20 ABI
        self.erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [
                    {"name": "_owner", "type": "address"},
                    {"name": "_spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }
        ]
        
        # LI.FI合约ABI（部分）
        self.lifi_abi = [
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "_transactionId", "type": "bytes32"},
                    {"internalType": "string", "name": "_integrator", "type": "string"},
                    {"internalType": "string", "name": "_referrer", "type": "string"},
                    {"internalType": "address payable", "name": "_receiver", "type": "address"},
                    {"internalType": "uint256", "name": "_minAmountOut", "type": "uint256"},
                    {
                        "components": [
                            {"internalType": "address", "name": "callTo", "type": "address"},
                            {"internalType": "address", "name": "approveTo", "type": "address"},
                            {"internalType": "address", "name": "sendingAssetId", "type": "address"},
                            {"internalType": "address", "name": "receivingAssetId", "type": "address"},
                            {"internalType": "uint256", "name": "fromAmount", "type": "uint256"},
                            {"internalType": "bytes", "name": "callData", "type": "bytes"},
                            {"internalType": "bool", "name": "requiresDeposit", "type": "bool"}
                        ],
                        "internalType": "struct LibSwap.SwapData",
                        "name": "_swapData",
                        "type": "tuple"
                    }
                ],
                "name": "swapTokensSingleV3ERC20ToERC20",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]

    def get_transaction_data(self, route_data, wallet_address):
        """从路由数据中提取交易信息并调用quote API (修复)"""
        try:
            route = route_data['routes'][0]
            
            # 使用LI.FI的quote API获取交易数据 - 使用GET请求
            url = f"{self.base_url}/v1/quote"
            params = {
                "fromChain": self.chain_id,
                "toChain": self.chain_id,
                "fromToken": self.usdc_address,
                "toToken": self.ussi_address,
                "fromAddress": wallet_address,
                "fromAmount": route['fromAmount'],
                "integrator": self.integrator,
                "slippage": self.slippage
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            quote_data = response.json()
            
            # 提取交易数据
            tx_data = quote_data.get('transactionRequest', {})
            logger.info(f"获取到交易数据: {len(tx_data.get('data', ''))} 字符")
            
            return tx_data
            
        except Exception as e:
            logger.error(f"获取交易数据失败: {e}")
            return None

    def get_routes(self, from_address, amount):
        """获取LI.FI路由 (根据实际API调用修复)"""
        url = f"{self.base_url}/v1/advanced/routes"
        
        payload = {
            "fromChainId": self.chain_id,
            "toChainId": self.chain_id,
            "fromTokenAddress": self.usdc_address,
            "toTokenAddress": self.ussi_address,
            "fromAddress": from_address,
            "fromAmount": str(amount),
            "options": {
                "integrator": self.integrator,
                "slippage": self.slippage
            }
        }
        print(payload)
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取路由失败: {e}")
            return None

    def get_usdc_balance(self, wallet_address):
        """获取USDC余额"""
        try:
            usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.usdc_address),
                abi=self.erc20_abi
            )
            balance = usdc_contract.functions.balanceOf(wallet_address).call()
            return balance
        except Exception as e:
            logger.error(f"获取USDC余额失败: {e}")
            return 0

    def check_allowance(self, wallet_address, spender_address):
        """检查USDC授权额度"""
        try:
            usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.usdc_address),
                abi=self.erc20_abi
            )
            allowance = usdc_contract.functions.allowance(wallet_address, spender_address).call()
            return allowance
        except Exception as e:
            logger.error(f"检查授权额度失败: {e}")
            return 0

    def approve_usdc(self, private_key, spender_address, amount):
        """授权USDC"""
        try:
            account = Account.from_key(private_key)
            wallet_address = account.address
            
            usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.usdc_address),
                abi=self.erc20_abi
            )
            
            # 构建交易
            transaction = usdc_contract.functions.approve(
                Web3.to_checksum_address(spender_address),
                amount
            ).build_transaction({
                'from': wallet_address,
                'nonce': self.w3.eth.get_transaction_count(wallet_address),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.chain_id
            })
            
            # 签名并发送交易
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            logger.info(f"授权交易已发送: {tx_hash.hex()}")
            
            # 等待交易确认
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            if receipt.status == 1:
                logger.info("授权交易成功")
                return True
            else:
                logger.error("授权交易失败")
                return False
                
        except Exception as e:
            logger.error(f"授权USDC失败: {e}")
            return False

    def execute_swap(self, private_key, route_data):
        """执行代币交换 (恢复原始逻辑)"""
        try:
            account = Account.from_key(private_key)
            wallet_address = account.address
            
            # 获取完整的交易数据
            tx_request = self.get_transaction_data(route_data, wallet_address)
            if not tx_request:
                logger.error("无法获取交易数据")
                return None
            
        except Exception as e:
            logger.error(f"执行交换失败111: {e}")
            return None

        try:
            # 直接使用LI.FI返回的完整交易数据
            transaction = {
                'to': Web3.to_checksum_address(tx_request['to']),
                'data': tx_request['data'],
                'value': int(tx_request.get('value', '0x0'), 16) if isinstance(tx_request.get('value'), str) else int(tx_request.get('value', 0)),
                'from': wallet_address,
                'nonce': self.w3.eth.get_transaction_count(wallet_address),
                'gas': int(tx_request.get('gasLimit', '0x76c00'), 16) if isinstance(tx_request.get('gasLimit'), str) else 500000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.chain_id
            }
            
            logger.info(f"交易参数:")
            logger.info(f"  - to: {transaction['to']}")
            logger.info(f"  - value: {transaction['value']}")
            logger.info(f"  - data length: {len(transaction['data'])}")
            logger.info(f"  - gas: {transaction['gas']}")
            
            # 签名并发送交易
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            logger.info(f"交换交易已发送: {tx_hash.hex()}")
            
            # 等待交易确认
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            if receipt.status == 1:
                logger.info(f"交换交易成功: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                logger.error(f"交换交易失败: {tx_hash.hex()}")
                logger.error(f"Gas used: {receipt.gasUsed}/{receipt.cumulativeGasUsed}")
                logger.error(f"交易详情: https://basescan.org/tx/{tx_hash.hex()}")
                return None
                
        except Exception as e:
            logger.error(f"执行交换失败222: {e}")
            return None

    def buy_ussi_for_wallet(self, wallet_data):
        """为单个钱包购买USSI (恢复原始流程)"""
        try:
            private_key = wallet_data['private_key']
            wallet_address = wallet_data['address']  # 注意：文档中是'adress'，这里假设是'address'
            
            logger.info(f"开始为钱包 {wallet_address} 购买USSI")
            
            # 获取USDC余额
            usdc_balance = self.get_usdc_balance(wallet_address)
            if usdc_balance < 0.5:
                logger.warning(f"钱包 {wallet_address} USDC余额少于0.5，跳过")
                return False
            
            logger.info(f"钱包USDC余额: {usdc_balance / 10**6:.2f} USDC")
            
            # 获取路由
            route_data = self.get_routes(wallet_address, usdc_balance)
            if not route_data or not route_data.get('routes'):
                logger.error("获取路由失败")
                return False
            
            route = route_data['routes'][0]
            logger.info(f"预计获得: {int(route['toAmount']) / 10**8:.8f} USSI")
            
            # 检查授权
            approval_address = route['steps'][0]['estimate']['approvalAddress']
            allowance = self.check_allowance(wallet_address, approval_address)
            
            if allowance < usdc_balance:
                logger.info(f"需要授权USDC给地址: {approval_address}")
                if not self.approve_usdc(private_key, approval_address, usdc_balance * 2):  # 授权2倍金额避免频繁授权
                    logger.error("授权失败")
                    return False
                time.sleep(5)  # 等待授权确认
            
            # 执行交换
            tx_hash = self.execute_swap(private_key, route_data)
            if tx_hash:
                logger.info(f"钱包 {wallet_address} 购买成功，交易哈希: {tx_hash}")
                return True
            else:
                logger.error(f"钱包 {wallet_address} 购买失败")
                return False
                
        except Exception as e:
            logger.error(f"钱包 {wallet_data.get('address', 'unknown')} 购买失败: {e}")
            return False

    def buy_ussi_batch(self, wallets):
        """批量购买USSI"""
        successful_purchases = []
        failed_purchases = []
        
        for i, wallet in enumerate(wallets):
            logger.info(f"处理钱包 {i+1}/{len(wallets)}")
            
            try:
                if self.buy_ussi_for_wallet(wallet):
                    successful_purchases.append(wallet['address'])
                else:
                    failed_purchases.append(wallet['address'])
            except Exception as e:
                logger.error(f"处理钱包失败: {e}")
                failed_purchases.append(wallet.get('address', 'unknown'))
            
            # 添加延迟避免频率限制
            if i < len(wallets) - 1:
                time.sleep(random.randint(15, 50))
        
        # 打印结果统计
        logger.info(f"购买完成！成功: {len(successful_purchases)}, 失败: {len(failed_purchases)}")
        if successful_purchases:
            logger.info(f"成功的钱包: {successful_purchases}")
        if failed_purchases:
            logger.info(f"失败的钱包: {failed_purchases}")






def get_wallet_from_mnemonic(mnemonic: str):
    """
    根据助记词生成钱包信息（ETH）

    Args:
        mnemonic (str): 助记词字符串（12 或 24 个单词）

    Returns:
        dict: 包含 address, private_key, public_key 的字典

    Raises:
        ValueError: 助记词非法
    """
    # 验证助记词合法性
    if not Bip39MnemonicValidator().IsValid(mnemonic):
        raise ValueError("助记词非法")

    # 生成种子
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()

    # 获取 BIP44 钱包（Ethereum）
    bip44_addr = (
        Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM)
        .Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
    )

    private_key = "0x"+ bip44_addr.PrivateKey().Raw().ToHex()
    public_key = bip44_addr.PublicKey().RawCompressed().ToHex()
    evm_address = bip44_addr.PublicKey().ToAddress()

    return {
        "address": evm_address,
        "private_key": private_key,
        "public_key": public_key
    }

def fetch_abi_base(contract_address, api_key):
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": 8453,
        "module": "contract",
        "action": "getabi",
        "address": contract_address,
        "apikey": api_key
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    if data.get("status") != "1":
        raise Exception(f"Error: {data.get('result')}")
    return json.loads(data["result"])

def get_mnemonic_by_env(env_name: str, wallet_type: str) -> Optional[str]:
    """根据单个环境名和钱包类型查询助记词"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT mnemonic FROM wallets WHERE environment_name = ? AND wallet_type = ?",
                (env_name, wallet_type)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"[错误] 查询环境 {env_name}（类型: {wallet_type}）失败: {e}")
        return None

def get_mnemonics_by_env_list(env_names: List[str], wallet_type: str) -> Dict[str, str]:
    """批量查询环境名对应的助记词"""
    mnemonics = {}
    for env in env_names:
        mnemonic = get_mnemonic_by_env(env, wallet_type)
        if mnemonic:
            mnemonics[env] = mnemonic
        else:
            print(f"[警告] 未找到环境 {env} 的助记词（类型: {wallet_type}）")
    return mnemonics

def main1():
    # 使用示例
    load_dotenv()
    ETHSACN_API_KEY = os.getenv("ETHSACN")
    print(ETHSACN_API_KEY)
    contract_addr = "0x3a46ed8fceb6ef1ada2e4600a522ae7e24d2ed18"  # USSI 代理合约
    contract_addr = "0xceb07a43477158d5f6d9a2d9bbeb58d40a1e19b7"  # USSI 真实合约
    env_names=['TW004-02', 'HK005-02', 'HK004-02', 'TW004-03', 'HK005-03', 'HK004-03', 'HK003-03', 'TW004-04', 'HK005-04', 'HK004-04', 'HK003-04', 'HK002-04', 'HK001-04', 'TW003-04', 'TW002-04', 'JAPA001-04', 'TW001-04', 'TW004-05', 'HK005-05', 'HK004-05', 'HK003-05', 'HK002-05', 'HK001-05', 'TW003-05', 'TW002-05', 'JAPA001-05', 'TW001-05', 'TW004-01', 'HK005-01', 'HK004-01']
    try:
        abi = fetch_abi_base(contract_addr, ETHSACN_API_KEY)
        print("ABI fetched successfully!")
        print(abi)
        # 可继续解析函数、构建交易等
    except Exception as e:
        print("Error fetching ABI:", e)

def get_wallets_by_env(env_names, wallet_type):
    mnemonic_dict = get_mnemonics_by_env_list(env_names, wallet_type)
    wallets = []
    for env, mnemonic in mnemonic_dict.items():
        wallet = get_wallet_from_mnemonic(mnemonic)
        wallet["env_name"] = env
        wallets.append(wallet)

    return wallets

def main():
    env_names1=['TW004-02', 'HK005-02', 'HK004-02', 
               'TW004-03', 'HK005-03', 'HK004-03', 
               'HK003-03', 'TW004-04', 'HK005-04', 
               'HK004-04', 'HK003-04', 'HK002-04', 
               'HK001-04', 'TW003-04', 'TW002-04', 
               'JAPA001-04', 'TW001-04', 'TW004-05', 
               'HK005-05', 'HK004-05', 'HK003-05', 
               'HK002-05', 'HK001-05', 'TW003-05', 
               'TW002-05', 'JAPA001-05', 'TW001-05', 
               'TW004-01', 'HK005-01', 'HK004-01'] 
    env_names2=[
        'TW001-01', 'TW001-02', 'TW001-03',
        'JAPA001-01', 'JAPA001-02', 'JAPA001-03',
        'TW002-01', 'TW002-02', 'TW002-03',
        'TW003-01', 'TW003-02', 'TW003-03',
        'HK001-01', 'HK001-02', 'HK001-03',
        'HK002-01', 'HK002-02', 'HK002-03',
        'HK003-01', 'HK003-02',
        'HK001-03'
    ]       
    # 钱包数据 - 需要填入实际数据
    #wallets = get_wallets_by_env(env_names1,"OKX")
    wallets = get_wallets_by_env(env_names2,"METAMASK")
    random.shuffle(wallets)
    # 验证钱包数据
    if not wallets or not wallets[0].get('private_key') or wallets[0]['private_key'] == "0x...":
        logger.error("钱包数据有误！")
        return
    
    # 创建买家实例
    buyer = USSIBuyer()
    
    # 执行批量购买
    buyer.buy_ussi_batch(wallets)    

if __name__ == "__main__":
    main()

