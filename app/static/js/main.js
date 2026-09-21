// Core UI scripts: Quick-add modal, notifications, and AJAX helpers

document.addEventListener("DOMContentLoaded", () => {
  // Setup Quick Add Modal
  const openBtn = document.getElementById("openQuickAddBtn");
  const modal = document.getElementById("quickAddModal");
  const closeBtn = document.getElementById("closeQuickAddBtn");
  const quickAddForm = document.getElementById("quickAddForm");

  if (openBtn && modal) {
    openBtn.addEventListener("click", () => {
      modal.classList.add("show");
      const amtInput = document.getElementById("qa_amount");
      if (amtInput) amtInput.focus();
    });
  }

  if (closeBtn && modal) {
    closeBtn.addEventListener("click", () => {
      modal.classList.remove("show");
    });
  }

  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.classList.remove("show");
      }
    });
  }

  // Handle Quick Add AJAX submission
  if (quickAddForm) {
    quickAddForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const submitBtn = quickAddForm.querySelector("button[type='submit']");
      const originalText = submitBtn.innerHTML;
      submitBtn.innerHTML = "Saving...";
      submitBtn.disabled = true;

      const payload = {
        amount: document.getElementById("qa_amount").value,
        category_id: document.getElementById("qa_category").value,
        date: document.getElementById("qa_date").value,
        payment_method: document.getElementById("qa_payment").value,
        need_want: document.getElementById("qa_need_want").value,
        notes: document.getElementById("qa_notes").value
      };

      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

      try {
        const response = await fetch("/api/expenses", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken || ""
          },
          body: JSON.stringify(payload)
        });

        const resData = await response.json();
        if (response.ok && resData.success) {
          modal.classList.remove("show");
          quickAddForm.reset();
          // Reload or trigger dashboard update
          window.location.reload();
        } else {
          alert("Error: " + (resData.error || "Could not log expense."));
        }
      } catch (err) {
        alert("Failed to submit expense: " + err.message);
      } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
      }
    });
  }
});
