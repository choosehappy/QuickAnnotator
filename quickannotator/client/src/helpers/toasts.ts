import { toast } from "react-toastify";


export function addPendingToast() {
    const checkCondition = async () => {
        try {
            const response = await fetch('/api/check-condition'); // Replace with your endpoint
            const data = await response.json();
            if (data.conditionMet) {
                return Promise.resolve();
            } else {
                throw new Error('Condition not met');
            }
        } catch (error) {
            throw new Error('Error checking condition');
        }
    };

    const pollCondition = () => new Promise(async (resolve, reject) => {
        const interval = setInterval(async () => {
            try {
                await checkCondition();
                clearInterval(interval);
                resolve('Condition met');
            } catch (error) {
                // Keep polling until condition is met
            }
        }, 3000); // Poll every 3 seconds
    });

    toast.promise(
        pollCondition(),
        {
            pending: 'Checking condition...',
            success: 'Condition met 👌',
            error: 'Failed to meet condition 🤯',
        }
    );
}

type Toast