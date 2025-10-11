// script.js
document.addEventListener('DOMContentLoaded', function() {
  const predictionForm = document.getElementById('prediction-form');
  const resultsCard = document.getElementById('results-card');
  
  predictionForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      // Show loading indicator
      showLoading(true);
      
      // Collect form data
      const flightData = {
          flight_number: document.getElementById('flight-number').value,
          airline: document.getElementById('airline').value,
          departure_airport: document.getElementById('departure-airport').value,
          arrival_airport: document.getElementById('arrival-airport').value,
          scheduled_departure: `${document.getElementById('scheduled-date').value}T${document.getElementById('scheduled-time').value}:00`
      };
      
      try {
          // Make API request to backend
          const response = await fetch('/api/predict', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify(flightData),
          });
          
          if (!response.ok) {
              throw new Error('API request failed');
          }
          
          const result = await response.json();
          
          // Display results
          displayResults(result);
          
          // Show results card
          resultsCard.classList.remove('d-none');
      } catch (error) {
          console.error('Error:', error);
          alert('An error occurred during prediction. Please try again.');
      } finally {
          // Hide loading indicator
          showLoading(false);
      }
  });
  
  function displayResults(result) {
      // Update delay probability gauge
      const probabilityBar = document.getElementById('delay-probability-bar');
      const probabilityText = document.getElementById('delay-probability-text');
      const probability = result.delay_probability * 100;
      
      probabilityBar.style.width = `${probability}%`;
      probabilityBar.setAttribute('aria-valuenow', probability);
      probabilityText.textContent = `${probability.toFixed(1)}%`;
      
      // Set color based on probability
      if (probability < 30) {
          probabilityBar.classList.add('bg-success');
      } else if (probability < 70) {
          probabilityBar.classList.add('bg-warning');
      } else {
          probabilityBar.classList.add('bg-danger');
      }
      
      // Display estimated delay
      const delayEstimate = document.getElementById('delay-estimate');
      if (result.prediction > 0) {
          const delayMinutes = Math.round(result.prediction);
          delayEstimate.textContent = `${delayMinutes} min`;
      } else {
          delayEstimate.textContent = 'On time';
      }
      
      // Display contributing factors
      const factorsList = document.getElementById('factors-list');
      factorsList.innerHTML = ''; // Clear previous factors
      
      Object.entries(result.factors).forEach(([factor, importance]) => {
          const listItem = document.createElement('li');
          listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
          listItem.textContent = factor;
          
          const badge = document.createElement('span');
          badge.className = 'badge bg-primary rounded-pill';
          badge.textContent = (importance * 100).toFixed(1) + '%';
          
          listItem.appendChild(badge);
          factorsList.appendChild(listItem);
      });
  }
  
  function showLoading(isLoading) {
      const submitButton = predictionForm.querySelector('button[type="submit"]');
      if (isLoading) {
          submitButton.disabled = true;
          submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
      } else {
          submitButton.disabled = false;
          submitButton.textContent = 'Predict Delay';
      }
  }
});