document.addEventListener('DOMContentLoaded', ready);

function ready(){   
    document.querySelectorAll(".plan-subscribe").forEach(link => {
        link.addEventListener("click", function (e) {
            e.preventDefault();

            const planId = parseInt(this.dataset.planId);
            const url = planId === 1 ? "/subscribe_free_plan" : "/start_subscription";

            fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    user_id: USER_ID,  // Expose this from Flask: const USER_ID = "{{ current_user.id }}";
                    plan_id: planId
                })
            })
            .then(res => res.json())
            .then(data => {
                if (planId === 1 && data.success) {
                    alert("Free plan activated!");
                    window.location.href = "/profile";
                } else if (planId !== 1 && data.authorization_url) {
                    window.location.href = data.authorization_url;  // Redirect to Paystack
                } else {
                    alert("Something went wrong: " + (data.error || "Unknown error"));
                }
            })
            .catch(err => {
                console.error(err);
                alert("An error occurred while processing your request.");
            });
        });
    });
}