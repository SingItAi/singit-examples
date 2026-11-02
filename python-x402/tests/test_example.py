import base64
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from eth_account import Account
from singit import SingItPaymentError
import example

# Invented test recipients, used only by the local merchant.
PAY_TO = "0x0000000000000000000000000000000000000042"


def encode(value):
    return base64.b64encode(json.dumps(value).encode()).decode()


@pytest.fixture
def merchant(server):
    offer = {"scheme": "upto", "network": "eip155:84532",
             "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
             "payTo": PAY_TO, "amount": "2000", "maxTimeoutSeconds": 120,
             "extra": {"facilitatorAddress": "0x0000000000000000000000000000000000000043",
                       "assetTransferMethod": "permit2", "name": "USDC", "version": "2",
                       "billing": {"mode": "actual_usage", "maxChargeAtomic": "2000"}}}
    def challenge(**overrides):
        selected = dict(offer, **overrides)
        body = {"x402Version": 2, "resource": {"url": server.url + "/v1/chat/completions"}, "accepts": [selected]}
        return 402, {"error": "Payment required."}, {"PAYMENT-REQUIRED": encode(body)}
    server.challenge = challenge
    server.success = (200, {"choices": [{"message": {"content": "pong"}}],
                            "billing": {"totalAtomic": "1000"}}, {})
    return server


@pytest.fixture
def env(merchant):
    return {"SINGIT_ALLOW_PAID": "1", "AGENT_PRIVATE_KEY": Account.create().key.hex(),
            "SINGIT_BASE_URL": merchant.url, "SINGIT_MAX_PER_CALL_USD": "0.003",
            "SINGIT_MAX_PER_DAY_USD": "0.002"}


def client(env):
    return example.paid_client(env, network="base-sepolia", pay_to=PAY_TO)


@pytest.mark.parametrize("change,match", [({"amount": "4000"}, "per-call ceiling"),
    ({"payTo": "0x0000000000000000000000000000000000000044"}, "Unexpected payee")])
def test_refusal_before_signing(merchant, env, monkeypatch, change, match):
    buyer = client(env)
    def no_sign(*args):
        pytest.fail("Refused offer reached signing")
    monkeypatch.setattr(buyer, "_sign", no_sign)
    merchant.replies = [merchant.challenge(**change)]
    with pytest.raises(SingItPaymentError, match=match):
        example.ask("ping", buyer)
    assert len(merchant.requests) == 1
    assert not merchant.requests[0][1].get("PAYMENT-SIGNATURE")


def test_signed_upto_and_daily_ceiling(merchant, env):
    buyer = client(env)
    merchant.replies = [merchant.challenge(), merchant.success, merchant.challenge()]
    answer = example.ask("ping", buyer)
    assert answer["payment"] == {"scheme": "upto", "network": "base-sepolia", "amountAtomic": "1000"}
    payload = json.loads(base64.b64decode(merchant.requests[1][1]["PAYMENT-SIGNATURE"]))
    assert len(merchant.requests) == 2
    assert payload["payload"]["signature"].startswith("0x")
    # Recover the actual Permit2 EIP-712 signature, without any RPC.
    from eth_account.messages import encode_typed_data
    auth = payload["payload"]["permit2Authorization"]
    domain = {"name": "Permit2", "chainId": 84532,
              "verifyingContract": "0x000000000022D473030F116dDEE9F6B43aC78BA3"}
    types = {
        "PermitWitnessTransferFrom": [{"name": "permitted", "type": "TokenPermissions"},
            {"name": "spender", "type": "address"}, {"name": "nonce", "type": "uint256"},
            {"name": "deadline", "type": "uint256"}, {"name": "witness", "type": "Witness"}],
        "TokenPermissions": [{"name": "token", "type": "address"}, {"name": "amount", "type": "uint256"}],
        "Witness": [{"name": "to", "type": "address"}, {"name": "facilitator", "type": "address"},
                    {"name": "validAfter", "type": "uint256"}],
    }
    signed = encode_typed_data(domain_data=domain, message_types=types, message_data={
        "permitted": {"token": auth["permitted"]["token"], "amount": int(auth["permitted"]["amount"])},
        "spender": auth["spender"], "nonce": int(auth["nonce"]), "deadline": int(auth["deadline"]),
        "witness": dict(auth["witness"], validAfter=int(auth["witness"]["validAfter"])),
    })
    assert Account.recover_message(signed, signature=payload["payload"]["signature"]).lower() == auth["from"].lower()
    assert payload["accepted"]["amount"] == "2000"
    assert payload["payload"]["permit2Authorization"]["from"].lower() == Account.from_key(env["AGENT_PRIVATE_KEY"]).address.lower()
    with pytest.raises(SingItPaymentError, match="Daily spend cap"):
        example.ask("ping", buyer)
    assert len(merchant.requests) == 3
    assert sum(bool(r[1].get("PAYMENT-SIGNATURE")) for r in merchant.requests) == 1


def test_free_mode(merchant, env, monkeypatch, capsys):
    for k,v in env.items(): monkeypatch.setenv(k,v)
    monkeypatch.delenv("SINGIT_ALLOW_PAID")
    merchant.replies = [merchant.challenge()]
    assert example.main(["ping"]) == 0
    assert "upto eip155:84532 2000" in capsys.readouterr().out
    assert len(merchant.requests) == 1
    assert not merchant.requests[0][1].get("PAYMENT-SIGNATURE")


def test_paid_requires_opt_in():
    env = {}
    with pytest.raises(RuntimeError, match="SINGIT_ALLOW_PAID=1"):
        client(env)


def test_snippet_compiles():
    compile(Path("snippet.py").read_text(), "snippet.py", "exec")
