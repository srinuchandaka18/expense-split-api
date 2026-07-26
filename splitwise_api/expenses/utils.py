from collections import defaultdict

def calculate_net_balances(group):
    balances = defaultdict(float)
    for expense in group.expenses.all():
        balances[expense.paid_by_id] += float(expense.amount)      # payer is owed
        for split in expense.splits.all():
            balances[split.user_id] -= float(split.share_amount)   # each person owes their share
    for settlement in group.settlements.all():
        balances[settlement.from_user_id] += float(settlement.amount)
        balances[settlement.to_user_id] -= float(settlement.amount)
    return {uid: round(bal, 2) for uid, bal in balances.items() if round(bal, 2) != 0}

def simplify_debts(balances):
    debtors = sorted([(uid, -bal) for uid, bal in balances.items() if bal < 0], key=lambda x: x[1], reverse=True)
    creditors = sorted([(uid, bal) for uid, bal in balances.items() if bal > 0], key=lambda x: x[1], reverse=True)

    transactions = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, owe = debtors[i]
        creditor_id, receive = creditors[j]
        settle = round(min(owe, receive), 2)
        if settle > 0:
            transactions.append({'from_user': debtor_id, 'to_user': creditor_id, 'amount': settle})
        owe, receive = round(owe - settle, 2), round(receive - settle, 2)
        debtors[i], creditors[j] = (debtor_id, owe), (creditor_id, receive)
        if owe == 0: i += 1
        if receive == 0: j += 1
    return transactions