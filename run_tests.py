import subprocess
import os
from datetime import datetime

def run_tests():
    # Create reports directory if it doesn't exist
    reports_dir = "test_reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Run tests and save output to file
    test_output_file = f"{reports_dir}/test_results_{timestamp}.txt"
    with open(test_output_file, 'w') as f:
        subprocess.run([
            "pytest", "-v", 
            "--cov=.", 
            "--cov-report=term-missing",
            "--cov-report=html:test_reports/coverage_html",
            "--cov-report=xml:test_reports/coverage.xml",
            "tests/"
        ], stdout=f, stderr=subprocess.STDOUT)

    print(f"\nTest results saved to: {test_output_file}")
    print("HTML coverage report saved to: test_reports/coverage_html/index.html")
    print("XML coverage report saved to: test_reports/coverage.xml")

if __name__ == "__main__":
    run_tests() 