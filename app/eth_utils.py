from web3 import Web3

INFURA_URL = "https://sepolia.infura.io/v3/본인_INFURA_KEY"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

CONTRACT_ADDRESS = "0xYourContractAddress"
CONTRACT_ABI = [...]  # 배포 후 실제 ABI로 교체

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

def mint_token(to_address, amount):
    # 실제론 관리자 지갑의 프라이빗키 필요
    # 트랜잭션 생성/서명/전송 예시
    pass 