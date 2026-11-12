document.getElementById('add-btn').addEventListener('click', function() {
    const nameInput = document.getElementById('expense-name');
    const amountInput = document.getElementById('expense-amount');
    const list = document.getElementById('expense-list');
    const totalSpan = document.getElementById('total-amount');

    const name = nameInput.value;
    const amount = parseFloat(amountInput.value);

    if (name && !isNaN(amount) && amount > 0) {
        const listItem = document.createElement('li');
        listItem.innerHTML = `<span>${name}</span><span>$${amount.toFixed(2)}</span>`;
        list.appendChild(listItem);

        let currentTotal = parseFloat(totalSpan.innerText);
        totalSpan.innerText = (currentTotal + amount).toFixed(2);

        nameInput.value = '';
        amountInput.value = '';
    } else {
        alert('Please enter a valid expense name and amount.');
    }
});