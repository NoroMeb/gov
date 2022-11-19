import time
from scripts.utils import (
    get_account,
    encode_function_data,
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
)
from brownie import (
    GovernanceTimeLock,
    GoatToken,
    MyGovernor,
    Box,
    Contract,
    network,
    accounts,
    chain,
)
from web3 import Web3, constants

MIN_DELAY = 1

QUORUM_PERCENTAGE = 4
VOTING_PERIOD = 50107
VOTING_DELAY = 1

PROPOSAL_DESCRIPTION = "Proposal #1: Store 1 in the Box!"

NEW_STORE_VALUE = 5


def main():

    account = get_account()
    goat_token = GoatToken[-1]
    time_lock = GovernanceTimeLock[-1]
    governor = MyGovernor[-1]
    box = Box[-1]
    proposal_id = propose(NEW_STORE_VALUE)
    print(f"Proposal ID {proposal_id}")
    # We do this just to move the blocks along
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        move_blocks(1)
    vote(proposal_id, 1)
    # Once the voting period is over,
    # if quorum was reached (enough voting power participated)
    # and the majority voted in favor, the proposal is
    # considered successful and can proceed to be executed.
    # To execute we must first `queue` it to pass the timelock
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        move_blocks(VOTING_PERIOD)
    # States: {Pending, Active, Canceled, Defeated, Succeeded, Queued, Expired, Executed }
    print(f" This proposal is currently {MyGovernor[-1].state(proposal_id)}")
    queue_and_execute(NEW_STORE_VALUE)


def deploy_time_lock():
    account = get_account()
    time_lock = GovernanceTimeLock.deploy(
        MIN_DELAY, [], [], {"from": account}, publish_source=True
    )

    return time_lock


def deploy_goat_token():
    account = get_account()
    goat_token = GoatToken[-1]
    goat_token.delegate(account, {"from": account})
    return goat_token


def deploy_box():
    account = get_account()
    box = Box.deploy({"from": account})
    tx = box.transferOwnership(GovernanceTimeLock[-1])
    tx.wait(1)


def propose(store_value):
    account = get_account()
    # We are going to store the number 1
    # With more args, just add commas and the items
    # This is a tuple
    # If no arguments, use `eth_utils.to_bytes(hexstr="0x")`
    args = (store_value,)
    # We could do this next line with just the Box object
    # But this is to show it can be any function with any contract
    # With any arguments
    encoded_function = Contract.from_abi("Box", Box[-1], Box.abi).store.encode_input(
        *args
    )
    print(encoded_function)
    propose_tx = MyGovernor[-1].propose(
        [Box[-1].address],
        [0],
        [encoded_function],
        PROPOSAL_DESCRIPTION,
        {"from": account},
    )
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        tx = account.transfer(accounts[0], "0 ether")
        tx.wait(1)
    propose_tx.wait(2)  # We wait 2 blocks to include the voting delay
    # This will return the proposal ID, brownie.exceptions.EventLookupError will be
    # thrown if ProposalCreated event is not emitted.
    proposal_id = propose_tx.events["ProposalCreated"][
        "proposalId"
    ]  # you could also do `propose_tx.return_value` if your node allows
    print(f"Proposal state {MyGovernor[-1].state(proposal_id)}")
    print(f"Proposal snapshot {MyGovernor[-1].proposalSnapshot(proposal_id)}")
    print(f"Proposal deadline {MyGovernor[-1].proposalDeadline(proposal_id)}")
    return proposal_id


def vote(proposal_id: int, vote: int):
    # 0 = Against, 1 = For, 2 = Abstain for this example
    # you can all the #COUNTING_MODE() function to see how to vote otherwise
    print(f"voting yes on {proposal_id}")
    account = get_account()
    tx = MyGovernor[-1].castVoteWithReason(
        proposal_id, vote, "Cuz I lika do da cha cha", {"from": account}
    )
    tx.wait(1)
    print(tx.events["VoteCast"])


def queue_and_execute(store_value):
    account = get_account()
    # time.sleep(VOTING_PERIOD + 1)
    # we need to explicity give it everything, including the description hash
    # it gets the proposal id like so:
    # uint256 proposalId = hashProposal(targets, values, calldatas, descriptionHash);
    # It's nearlly exactly the same as the `propose` function, but we hash the description
    args = (store_value,)
    encoded_function = Contract.from_abi("Box", Box[-1], Box.abi).store.encode_input(
        *args
    )
    # this is the same as ethers.utils.id(description)
    description_hash = Web3.keccak(text=PROPOSAL_DESCRIPTION).hex()
    tx = MyGovernor[-1].queue(
        [Box[-1].address],
        [0],
        [encoded_function],
        description_hash,
        {"from": account},
    )
    tx.wait(1)

    if network.show_active() == "development":
        time.sleep(1)

    tx = MyGovernor[-1].execute(
        [Box[-1].address],
        [0],
        [encoded_function],
        description_hash,
        {"from": account},
    )
    tx.wait(1)
    print(Box[-1].retrieve())


def move_blocks(amount):
    for block in range(amount):
        get_account().transfer(get_account(), "0 ether")
    print(chain.height)
