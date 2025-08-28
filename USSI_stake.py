import logging
from web3 import Web3
from web3.exceptions import ContractLogicError
from decimal import Decimal
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


# 简化版的ERC20 ABI，包含质押所需的函数
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]

# 质押合约的完整ABI
STAKING_ABI = [
    {"inputs":[],"stateMutability":"nonpayable","type":"constructor"},
    {"inputs":[{"internalType":"address","name":"target","type":"address"}],"name":"AddressEmptyCode","type":"error"},
    {"inputs":[{"internalType":"address","name":"implementation","type":"address"}],"name":"ERC1967InvalidImplementation","type":"error"},
    {"inputs":[],"name":"ERC1967NonPayable","type":"error"},
    {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"allowance","type":"uint256"},
               {"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientAllowance","type":"error"},
    {"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"uint256","name":"balance","type":"uint256"},
               {"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientBalance","type":"error"},
    {"inputs":[{"internalType":"address","name":"approver","type":"address"}],"name":"ERC20InvalidApprover","type":"error"},
    {"inputs":[{"internalType":"address","name":"receiver","type":"address"}],"name":"ERC20InvalidReceiver","type":"error"},
    {"inputs":[{"internalType":"address","name":"sender","type":"address"}],"name":"ERC20InvalidSender","type":"error"},
    {"inputs":[{"internalType":"address","name":"spender","type":"address"}],"name":"ERC20InvalidSpender","type":"error"},
    {"inputs":[],"name":"EnforcedPause","type":"error"},{"inputs":[],"name":"ExpectedPause","type":"error"},
    {"inputs":[],"name":"FailedCall","type":"error"},{"inputs":[],"name":"InvalidInitialization","type":"error"},
    {"inputs":[],"name":"NotInitializing","type":"error"},
    {"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"OwnableInvalidOwner","type":"error"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"OwnableUnauthorizedAccount","type":"error"},
    {"inputs":[{"internalType":"address","name":"token","type":"address"}],"name":"SafeERC20FailedOperation","type":"error"},
    {"inputs":[],"name":"UUPSUnauthorizedCallContext","type":"error"},
    {"inputs":[{"internalType":"bytes32","name":"slot","type":"bytes32"}],"name":"UUPSUnsupportedProxiableUUID","type":"error"},
    {"anonymous":False,
     "inputs":[{"indexed":True,"internalType":"address","name":"owner","type":"address"},
                                 {"indexed":True,"internalType":"address","name":"spender","type":"address"},
                                 {"indexed":False,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":False,"internalType":"uint64","name":"version","type":"uint64"}],"name":"Initialized","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"previousOwner","type":"address"},
                                 {"indexed":True,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":False,"internalType":"address","name":"account","type":"address"}],"name":"Paused","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":False,"internalType":"uint48","name":"oldCooldown","type":"uint48"},
                                 {"indexed":False,"internalType":"uint48","name":"cooldown","type":"uint48"}],"name":"SetCooldown","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":False,"internalType":"address","name":"staker","type":"address"},
                                 {"indexed":False,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Stake","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"from","type":"address"},
                                 {"indexed":True,"internalType":"address","name":"to","type":"address"},
                                 {"indexed":False,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":False,"internalType":"address","name":"unstaker","type":"address"},
                                 {"indexed":False,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"UnStake","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":False,"internalType":"address","name":"account","type":"address"}],"name":"Unpaused","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"implementation","type":"address"}],"name":"Upgraded","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":False,"internalType":"address","name":"withdrawer","type":"address"},
                                 {"indexed":False,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Withdraw","type":"event"},
    {"inputs":[],"name":"MAX_COOLDOWN","outputs":[{"internalType":"uint48","name":"","type":"uint48"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"UPGRADE_INTERFACE_VERSION","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],
     "name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],
     "name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],
     "name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"cooldown","outputs":[{"internalType":"uint48","name":"","type":"uint48"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"cooldownInfos",
     "outputs":[{"internalType":"uint256","name":"cooldownAmount","type":"uint256"},{"internalType":"uint256","name":"cooldownEndTimestamp","type":"uint256"}],
     "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"string","name":"name_","type":"string"},{"internalType":"string","name":"symbol_","type":"string"},
               {"internalType":"address","name":"token_","type":"address"},{"internalType":"uint48","name":"cooldown_","type":"uint48"},
               {"internalType":"address","name":"owner_","type":"address"}],"name":"initialize","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"pause","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"paused","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"proxiableUUID","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint48","name":"cooldown_","type":"uint48"}],"name":"setCooldown","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"stake","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"token","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],
     "name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},
                {"internalType":"uint256","name":"value","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],
     "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"unpause","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"unstake","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"newImplementation","type":"address"},
               {"internalType":"bytes","name":"data","type":"bytes"}],"name":"upgradeToAndCall","outputs":[],"stateMutability":"payable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"withdraw","outputs":[],"stateMutability":"nonpayable","type":"function"}
]

class USSIStaker:
    # 内置 RPC URL 和合约地址
    RPC_URL = "https://mainnet.base.org"
    USSI_ADDRESS = "0x3a46ed8fceb6ef1ada2e4600a522ae7e24d2ed18"
    STAKING_CONTRACT_ADDRESS = "0x7f811E881693af12D84976D59fF3Fb0Eaf135524"

    def __init__(self, private_key: str):
        """
        初始化USSI质押类。
        
        参数:
        private_key (str): 用于签署交易的钱包私钥。
        """
        self.w3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        self.private_key = private_key
        self.wallet_address = self.w3.eth.account.from_key(private_key).address
        
        # 将内置地址转换为校验和地址
        self.ussi_address = Web3.to_checksum_address(self.USSI_ADDRESS)
        self.staking_contract_address = Web3.to_checksum_address(self.STAKING_CONTRACT_ADDRESS)
        
        # 创建USSI代币合约实例
        self.ussi_contract = self.w3.eth.contract(address=self.ussi_address, abi=ERC20_ABI)
        # 创建质押合约实例
        self.staking_contract = self.w3.eth.contract(address=self.staking_contract_address, abi=STAKING_ABI)

    # 新增方法以获取USSI的小数位数
    def get_ussi_decimals(self) -> int:
        """获取USSI代币的小数位数。"""
        try:
            return self.ussi_contract.functions.decimals().call()
        except Exception as e:
            logger.error(f"获取USSI小数位数失败: {e}")
            return 18 # 默认返回18

    def get_ussi_balance(self) -> int:
        """获取钱包的USSI余额（最小单位）。"""
        try:
            balance = self.ussi_contract.functions.balanceOf(self.wallet_address).call()
            logger.info(f"USSI余额: {balance} (最小单位)")
            return balance
        except Exception as e:
            logger.error(f"获取USSI余额失败: {e}")
            return 0

    def check_allowance(self, amount_to_stake: int) -> bool:
        """检查质押合约的USSI授权额度是否足够。"""
        try:
            allowance = self.ussi_contract.functions.allowance(
                self.wallet_address,
                self.staking_contract_address
            ).call()
            logger.info(f"质押合约USSI授权额度: {allowance} (最小单位)")
            return allowance >= amount_to_stake
        except Exception as e:
            logger.error(f"检查授权额度失败: {e}")
            return False

    def approve_ussi(self, amount_to_approve: int) -> bool:
        """授权质押合约转移USSI代币。"""
        logger.info("开始授权质押合约...")
        try:
            # 构建授权交易
            approve_txn = self.ussi_contract.functions.approve(
                self.staking_contract_address,
                amount_to_approve
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'gas': 100000, # 授权交易的Gas Limit，通常100000足够
                'gasPrice': self.w3.eth.gas_price
            })

            # 签名并发送交易
            signed_txn = self.w3.eth.account.sign_transaction(approve_txn, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            logger.info(f"授权交易已发送, 哈希: {tx_hash.hex()}")
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            logger.info("授权交易成功！")
            return True
        except Exception as e:
            logger.error(f"授权失败: {e}")
            return False

    def stake_ussi(self, amount_to_stake: int) -> bool:
        """执行USSI质押操作。"""
        logger.info(f"开始质押 {amount_to_stake} (最小单位) USSI...")
        try:
            # 检查USSI余额
            balance = self.get_ussi_balance()
            if balance < amount_to_stake:
                logger.error(f"USSI余额不足。需要 {amount_to_stake}，但只有 {balance}")
                return False

            # 检查授权额度，如果不足则进行授权
            if not self.check_allowance(amount_to_stake):
                logger.info("授权额度不足，正在进行授权...")
                # 授权金额为需要质押的金额
                if not self.approve_ussi(amount_to_stake):
                    logger.error("授权失败，无法进行质押。")
                    return False
            
            # 构建质押交易
            stake_txn = self.staking_contract.functions.stake(
                amount_to_stake
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'gas': 500000, # 质押交易的Gas Limit，根据需要调整
                'gasPrice': self.w3.eth.gas_price
            })

            # 签名并发送交易
            signed_txn = self.w3.eth.account.sign_transaction(stake_txn, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            logger.info(f"质押交易已发送, 哈希: {tx_hash.hex()}")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                logger.info("质押成功！")
                return True
            else:
                logger.error("质押交易失败。")
                return False

        except ContractLogicError as e:
            logger.error(f"质押失败 (合约逻辑错误): {e}")
            return False
        except Exception as e:
            logger.error(f"质押失败: {e}")
            return False
        
    def get_staked_balance(self) -> int:
        """获取钱包在质押合约中的质押余额（最小单位）。"""
        try:
            staked_balance = self.staking_contract.functions.balanceOf(self.wallet_address).call()
            logger.info(f"钱包 {self.wallet_address} 质押余额: {staked_balance} (最小单位)")
            return staked_balance
        except Exception as e:
            logger.error(f"获取质押余额失败: {e}")
            return 0

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
        'HK003-01', 'HK003-02'
    ]       
    # 钱包数据 - 需要填入实际数据
    wallets = get_wallets_by_env(env_names1,"OKX")
    wallets = get_wallets_by_env(env_names2,"METAMASK")
    random.shuffle(wallets)
    # 验证钱包数据
    if not wallets or not wallets[0].get('private_key') or wallets[0]['private_key'] == "0x...":
        logger.error("钱包数据有误！")
        return
    
    stake(wallets)
    #stake_balance(wallets)


def stake(wallets):
    for i, wallet in enumerate(wallets):
        logger.info(f"--- 开始处理钱包 {i+1}/{len(wallets)} ---")
        try:
            private_key = wallet["private_key"]
            wallet_address = wallet["address"]
            wallet_env = wallet["env_name"]
            
            staker = USSIStaker(private_key)
            
            ussi_decimals = staker.get_ussi_decimals()
            balance_wei = staker.get_ussi_balance()
            
            # 转换为可读格式
            balance_readable = balance_wei / (10 ** ussi_decimals)
            
            logger.info(f"钱包 {wallet_env} 的 USSI 余额为 {balance_readable}")

            # 检查余额是否大于1.0
            if balance_readable > Decimal('1.0'):
                logger.info(f"余额大于1.0，开始质押...")
                staker.stake_ussi(balance_wei)
            else:
                logger.info("余额小于或等于1.0，跳过质押。")

        except Exception as e:
            logger.error(f"处理钱包 {wallet_env} 失败: {e}")
        
        time.sleep(random.randint(15, 100))
    logger.info("所有钱包处理完毕。")

def stake_balance(wallets):
    for i, wallet in enumerate(wallets):
        logger.info(f"--- 开始处理钱包 {i+1}/{len(wallets)} ---")
        try:
            private_key = wallet["private_key"]
            wallet_address = wallet["address"]
            wallet_env = wallet["env_name"]
            
            staker = USSIStaker(private_key)
            staker.get_staked_balance()

        except Exception as e:
                logger.error(f"处理钱包 {wallet_env} 失败: {e}")    

if __name__ == "__main__":
    main()

