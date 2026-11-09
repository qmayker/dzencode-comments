const CONFIG_ELEMENT_ID = "app-config";

function readConfig() {
  const element = document.getElementById(CONFIG_ELEMENT_ID);
  if (!element) {
    throw new Error("На странице отсутствует конфигурация приложения.");
  }
  return JSON.parse(element.textContent);
}

export const config = readConfig();
