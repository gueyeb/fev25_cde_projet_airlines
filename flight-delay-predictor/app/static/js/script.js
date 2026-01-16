// frontend/static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
  const predictionForm = document.getElementById('prediction-form');
  const resultsCard = document.getElementById('results-card');
  let factorsChart = null;
  
  // Set default date to today
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('scheduled-date').value = today;
  
  // Initialize Flatpickr for time
  flatpickr("#scheduled-time", {
      enableTime: true,
      noCalendar: true,
      dateFormat: "H:i",
      time_24hr: true,
      defaultDate: "12:00"
  });

  // Setup Autocomplete
  setupAutocomplete(
      'airline-search', 
      'airline', 
      'airline-results', 
      '/api/airlines/search', 
      item => `${item.code} - ${item.name}`,
      item => item.code
  );

  setupAutocomplete(
      'departure-search', 
      'departure-airport', 
      'departure-results', 
      '/api/airports/search', 
      item => `${item.code} - ${item.name} (${item.city || ''})`,
      item => item.code
  );

  setupAutocomplete(
      'arrival-search', 
      'arrival-airport', 
      'arrival-results', 
      '/api/airports/search', 
      item => `${item.code} - ${item.name} (${item.city || ''})`,
      item => item.code
  );

  setupFlightAutocomplete();

  
  predictionForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      // Validate inputs
      const airline = document.getElementById('airline').value;
      const depAirport = document.getElementById('departure-airport').value;
      const arrAirport = document.getElementById('arrival-airport').value;

      if (!depAirport || !arrAirport) {
          showErrorMessage('Please select valid airports from the list.');
          return;
      }

      showLoading(true);
      
      const flightData = {
          flight_number: document.getElementById('flight-number').value,
          airline: airline || null, // Optional
          departure_airport: depAirport,
          arrival_airport: arrAirport,
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
      // Display warning banner if using mock data
      if (result.using_mock_data && result.warning) {
          showWarningBanner(result.warning);
      } else {
          hideWarningBanner();
      }

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

  function showWarningBanner(message) {
      // Remove any existing warning banner
      hideWarningBanner();

      // Create warning banner
      const banner = document.createElement('div');
      banner.id = 'model-warning-banner';
      banner.className = 'alert alert-warning alert-dismissible fade show mb-4';
      banner.setAttribute('role', 'alert');
      banner.innerHTML = `
          <div class="d-flex align-items-center">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>
              <div>
                  <strong>Warning:</strong> ${message}
              </div>
          </div>
          <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      `;

      // Insert banner at the top of the results card
      const resultsCard = document.getElementById('results-card');
      const cardBody = resultsCard.querySelector('.card-body');
      cardBody.insertBefore(banner, cardBody.firstChild);
  }

  function hideWarningBanner() {
      const existingBanner = document.getElementById('model-warning-banner');
      if (existingBanner) {
          existingBanner.remove();
      }
  }

  // Check model status on page load
  async function checkModelStatus() {
      try {
          const response = await fetch('/api/health');
          const health = await response.json();

          if (!health.model_loaded) {
              // Show a persistent info message at the top of the page
              const infoDiv = document.createElement('div');
              infoDiv.id = 'model-status-info';
              infoDiv.className = 'alert alert-info alert-dismissible fade show';
              infoDiv.setAttribute('role', 'alert');
              infoDiv.innerHTML = `
                  <div class="d-flex align-items-center">
                      <i class="bi bi-info-circle-fill me-2"></i>
                      <div>
                          <strong>Note:</strong> ML model not loaded. Predictions will be simulated based on time patterns.
                      </div>
                  </div>
                  <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
              `;

              // Insert at the top of the main container
              const container = document.querySelector('.container');
              container.insertBefore(infoDiv, container.firstChild);
          }
      } catch (error) {
          console.error('Error checking model status:', error);
      }
  }

  // Autocomplete Implementation
  function setupAutocomplete(inputId, hiddenId, resultsId, endpoint, labelFormatter, valueFormatter) {
    const input = document.getElementById(inputId);
    const hiddenInput = document.getElementById(hiddenId);
    const resultsContainer = document.getElementById(resultsId);
    let debounceTimer;

    input.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();
        
        if (query.length < 2) {
            resultsContainer.innerHTML = '';
            resultsContainer.classList.add('d-none');
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const response = await fetch(`${endpoint}?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                resultsContainer.innerHTML = '';
                
                if (data.length > 0) {
                    data.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'list-group-item list-group-item-action autocomplete-item';
                        div.textContent = labelFormatter(item);
                        div.onclick = function() {
                            input.value = labelFormatter(item);
                            hiddenInput.value = valueFormatter(item);
                            resultsContainer.classList.add('d-none');
                        };
                        resultsContainer.appendChild(div);
                    });
                    resultsContainer.classList.remove('d-none');
                } else {
                    const div = document.createElement('div');
                    div.className = 'list-group-item disabled';
                    div.textContent = 'No results found';
                    resultsContainer.appendChild(div);
                    resultsContainer.classList.remove('d-none');
                }
            } catch (error) {
                console.error('Search error:', error);
            }
        }, 300);
    });

    // Close results when clicking outside
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !resultsContainer.contains(e.target)) {
            resultsContainer.classList.add('d-none');
        }
    });
    
    // Clear hidden value if input is cleared
    input.addEventListener('change', function() {
        if (!this.value) {
            hiddenInput.value = '';
        }
    });
  }

  function setupFlightAutocomplete() {
    const input = document.getElementById('flight-number');
    const resultsContainer = document.getElementById('flight-results');
    let debounceTimer;

    input.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();
        
        if (query.length < 2) {
            resultsContainer.innerHTML = '';
            resultsContainer.classList.add('d-none');
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const response = await fetch(`/api/flights/search?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                resultsContainer.innerHTML = '';
                
                if (data.length > 0) {
                    data.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'list-group-item list-group-item-action autocomplete-item';
                        div.innerHTML = `
                            <div class="d-flex justify-content-between">
                                <strong>${item.flight_number}</strong>
                                <small>${item.airline}</small>
                            </div>
                            <div class="small text-muted">
                                ${item.departure_airport} <i class="bi bi-arrow-right"></i> ${item.arrival_airport}
                            </div>
                        `;
                        div.onclick = function() {
                            // Fill Flight Number
                            input.value = item.flight_number;
                            
                            // Fill Airline
                            document.getElementById('airline').value = item.airline;
                            const airlineDisplay = item.airline_name ? `${item.airline} - ${item.airline_name}` : item.airline;
                            document.getElementById('airline-search').value = `${airlineDisplay} (Auto-filled)`;
                            
                            // Fill Departure
                            document.getElementById('departure-airport').value = item.departure_airport;
                            const depDisplay = item.departure_airport_name ? `${item.departure_airport} - ${item.departure_airport_name}` : item.departure_airport;
                            document.getElementById('departure-search').value = depDisplay;
                            
                            // Fill Arrival
                            document.getElementById('arrival-airport').value = item.arrival_airport;
                            const arrDisplay = item.arrival_airport_name ? `${item.arrival_airport} - ${item.arrival_airport_name}` : item.arrival_airport;
                            document.getElementById('arrival-search').value = arrDisplay;
                            
                            resultsContainer.classList.add('d-none');
                        };
                        resultsContainer.appendChild(div);
                    });
                    resultsContainer.classList.remove('d-none');
                } else {
                    const div = document.createElement('div');
                    div.className = 'list-group-item disabled';
                    div.textContent = 'No matching flights found';
                    resultsContainer.appendChild(div);
                    resultsContainer.classList.remove('d-none');
                }
            } catch (error) {
                console.error('Flight search error:', error);
            }
        }, 300);
    });

    // Close results when clicking outside
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !resultsContainer.contains(e.target)) {
            resultsContainer.classList.add('d-none');
        }
    });
  }

  // Check model status when page loads
  checkModelStatus();
});