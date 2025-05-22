// Lấy các thành phần trong form
const form = document.querySelector('form');
const username = form.querySelector('input[name="username"]');
const email = form.querySelector('input[name="email"]');
const password = form.querySelector('input[name="password"]');
const btn = document.querySelector('#login-btn');
const msg = document.querySelector('.msg');

// Ban đầu disable nút
btn.disabled = true;

function showMsg() {
    const isEmpty = username.value.trim() === '' || email.value.trim() === '' || password.value.trim() === '';

    if (isEmpty) {
        msg.innerText = 'Please fill all fields before signing up.';
        msg.style.color = 'rgb(218 49 49)';
        btn.disabled = true;
    } else {
        msg.innerText = 'All good! You can sign up now 🚀';
        msg.style.color = '#92ff92';
        btn.disabled = false;
    }
}

// Gắn event khi người dùng gõ vào input
form.addEventListener('input', showMsg);
