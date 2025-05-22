document.addEventListener("DOMContentLoaded", () => {
    const carousel = document.querySelector(".carousel");
    let scrollAmount = 0;
    setInterval(() => {
      scrollAmount += 1;
      carousel.scrollTo({ left: scrollAmount, behavior: "smooth" });
      if (scrollAmount >= carousel.scrollWidth - carousel.clientWidth) {
        scrollAmount = 0;
      }
    }, 40); // tốc độ cuộn
  });
  