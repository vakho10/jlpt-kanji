document.addEventListener('DOMContentLoaded', () => {
    // Enable tooltips on page
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
    const tooltipList = [...tooltipTriggerList]
        .map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))
})
