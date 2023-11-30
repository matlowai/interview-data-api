from logger import logger

# Normalizes claim amount irrespective of its format (string, float, etc.)
def normalize_claim_amount(amount):
    if isinstance(amount, str):
        amount = amount.replace('$', '').replace(',', '')
        return float(amount)
    return amount

# Analyzes a specific set of claims data (textfile or gptmsg)
def analyze_specific_claims_data(claims_data):
    category_counts = {}
    category_totals = {}

    for data in claims_data:
        try:
            category = data.get('Claims Category')
            amount = data.get('Claim Amount')

            if category and amount is not None:
                normalized_amount = normalize_claim_amount(amount)
                category_counts[category] = category_counts.get(category, 0) + 1
                category_totals[category] = category_totals.get(category, 0) + normalized_amount
        except Exception as e:
            logger.error(f"Error processing data: {e}")

    category_averages = {cat: category_totals[cat] / category_counts[cat] for cat in category_counts if category_counts[cat] > 0}
    return category_counts, category_averages

# Main function to analyze all claims
def analyze_claims(claims):
    textfile_data = [claim.get('analysis', {}).get('textfile_analysis', {}) for claim in claims]
    gptmsg_data = [claim.get('analysis', {}).get('gptmsg_analysis', {}) for claim in claims]

    textfile_counts, textfile_averages = analyze_specific_claims_data(textfile_data)
    gptmsg_counts, gptmsg_averages = analyze_specific_claims_data(gptmsg_data)

    return textfile_counts, textfile_averages, gptmsg_counts, gptmsg_averages
