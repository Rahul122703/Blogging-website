const navBar = document.querySelector("#mainNav");
window.addEventListener("scroll", () => {
  if (window.pageYOffset > navBar.getBoundingClientRect().height) {
    navBar.classList.add("is-visible", "is-fixed");
  } else {
    navBar.classList.remove("is-visible", "is-fixed");
  }
});
