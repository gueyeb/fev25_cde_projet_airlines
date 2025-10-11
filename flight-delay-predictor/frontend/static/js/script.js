// frontend/static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
  const predictionForm = document.getElementById('prediction-form');
  const resultsCard = document.getElementById('results-card');
  let factorsChart = null;
  
  // Set default date to today
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('scheduled-date').value = today;
  
  // Load airports from API
  loadAirports();
  
  predictionForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      showLoading(true);
      
      const flightData = {
          flight_number: document.getElementById('flight-number').value,
          airline: document.getElementById('airline').value,
          departure_airport: document.getElementById('departure-airport').value,
          arrival_airport: document.getElementById('arrival-airport').value,
          scheduled_departure: `${document.getElementById('scheduled-date').value}T${document.getElementById('scheduled-time').value}:00`
      };
      
      try {
          const response = await fetch('/api/predict', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify(flightData),
          });
          
          if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
          }
          
          const result = await response.json();
          displayResults(result);
          resultsCard.classList.remove('d-none');
          
          // Scroll to results
          resultsCard.scrollIntoView({ behavior: 'smooth' });
          
      } catch (error) {
          console.error('Error:', error);
          alert('An error occurred during prediction. Please try again.');
      } finally {
          showLoading(false);
      }
  });
  
  function displayResults(result) {
      const probabilityBar = document.getElementById('delay-probability-bar');
      const probabilityText = document.getElementById('delay-probability-text');
      const probability = result.delay_probability * 100;
      
      // Reset classes
      probabilityBar.className = 'progress-bar';
      
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
          delayEstimate.className = 'display-4 text-center text-danger';
      } else {
          delayEstimate.textContent = 'On time';
          delayEstimate.className = 'display-4 text-center text-success';
      }
      
      // Display contributing factors
      const factorsList = document.getElementById('factors-list');
      factorsList.innerHTML = '';
      
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
      
      // Create the factors chart
      createFactorsChart(result.factors);
  }
  
  function showLoading(isLoading) {
      const submitButton = predictionForm.querySelector('button[type="submit"]');
      if (isLoading) {
          submitButton.disabled = true;
          submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Processing...';
      } else {
          submitButton.disabled = false;
          submitButton.textContent = 'Predict Delay';
      }
  }
  
  async function loadAirports() {
      try {
          const response = await fetch('/api/airports');
          if (!response.ok) {
              throw new Error('Failed to load airports');
          }
          
          const airports = await response.json();
          const departureSelect = document.getElementById('departure-airport');
          const arrivalSelect = document.getElementById('arrival-airport');
          
          airports.forEach(airport => {
              const option1 = document.createElement('option');
              option1.value = airport.code;
              option1.textContent = `${airport.code} - ${airport.name}`;
              departureSelect.appendChild(option1);
              
              const option2 = document.createElement('option');
              option2.value = airport.code;
              option2.textContent = `${airport.code} - ${airport.name}`;
              arrivalSelect.appendChild(option2);
          });
      } catch (error) {
          console.error('Error loading airports:', error);
          showErrorMessage('Failed to load airports. Using manual input.');
      }
  }
  
  function createFactorsChart(factors) {
      const ctx = document.getElementById('factors-chart').getContext('2d');
      
      // Destroy existing chart if it exists
      if (factorsChart) {
          factorsChart.destroy();
      }
      
      const labels = Object.keys(factors);
      const data = Object.values(factors).map(val => (val * 100).toFixed(1));
      
      factorsChart = new Chart(ctx, {
          type: 'doughnut',
          data: {
              labels: labels,
              datasets: [{
                  data: data,
                  backgroundColor: [
                      '#FF6384',
                      '#36A2EB',
                      '#FFCE56',
                      '#4BC0C0',
                      '#9966FF'
                  ],
                  hoverBackgroundColor: [
                      '#FF6384',
                      '#36A2EB',
                      '#FFCE56',
                      '#4BC0C0',
                      '#9966FF'
                  ]
              }]
          },
          options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                  legend: {
                      position: 'bottom',
                      labels: {
                          boxWidth: 12,
                          font: {
                              size: 11
                          }
                      }
                  },
                  tooltip: {
                      callbacks: {
                          label: function(context) {
                              return context.label + ': ' + context.parsed + '%';
                          }
                      }
                  }
              }
          }
      });
  }
  
  function showErrorMessage(message) {
      // Create a toast notification
      const toast = document.createElement('div');
      toast.className = 'toast align-items-center text-bg-warning border-0 position-fixed top-0 end-0 m-3';
      toast.setAttribute('role', 'alert');
      toast.style.zIndex = '1055';
      toast.innerHTML = `
          <div class="d-flex">
              <div class="toast-body">
                  <i class="bi bi-exclamation-triangle me-2"></i>${message}
              </div>
              <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
          </div>
      `;
      
      document.body.appendChild(toast);
      const bsToast = new bootstrap.Toast(toast);
      bsToast.show();
      
      // Remove toast element after it's hidden
      toast.addEventListener('hidden.bs.toast', () => {
          document.body.removeChild(toast);
      });
  }
});