document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('input[name="amount"]').forEach(input => {
    input.addEventListener("input", () => {
      const n = Number(input.value);
      input.setCustomValidity(n <= 0 ? "Amount must be greater than zero." : (n > 50000 ? "Maximum demo transfer is ₹50,000." : ""));
    });
  });
});
