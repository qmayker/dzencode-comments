const CONFIG_ELEMENT_ID = "app-config";

function readConfig() {
  const element = document.getElementById(CONFIG_ELEMENT_ID);
  if (!element) {
    throw new Error("Application config is missing from the page.");
  }
  return JSON.parse(element.textContent);
}

export const config = readConfig();
