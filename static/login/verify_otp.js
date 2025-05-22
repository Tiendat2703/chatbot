document.addEventListener('DOMContentLoaded', () => {
    const resendLink = document.getElementById("resend-link");
    const countdown = document.getElementById("countdown");

    if (resendLink && countdown) {
        let secondsRemaining = 60;

        resendLink.style.pointerEvents = "none";
        resendLink.style.color = "#999";
        countdown.innerText = `(in ${secondsRemaining}s)`;

        const timer = setInterval(() => {
            secondsRemaining--;
            countdown.innerText = `(in ${secondsRemaining}s)`;

            if (secondsRemaining <= 0) {
                clearInterval(timer);
                countdown.innerText = "";
                resendLink.style.pointerEvents = "auto";
                resendLink.style.color = "#4db8ff";
            }
        }, 1000);
    }
});
