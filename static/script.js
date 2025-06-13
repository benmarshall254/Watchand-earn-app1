let counter = 0;
const counterElement = document.getElementById("counter");
const earnMsg = document.getElementById("earnMsg");

const timer = setInterval(() => {
  counter++;
  counterElement.innerText = counter;

  if (counter === 30) {
    clearInterval(timer);

    // Notify server about earnings
    fetch("/earn", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ earned: 0.0001 })
    });

    // Show earning message
    earnMsg.style.display = "block";
  }
}, 1000);
