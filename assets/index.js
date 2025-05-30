// Import custom Bootstrap theme
import './scss/main.scss';

function component() {
  const element = document.createElement("div");
  element.innerHTML = "Hello webpack";
  return element;
}
document.body.appendChild(component());
