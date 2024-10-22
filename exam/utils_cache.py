def get_cache_key_stats(prefix, test_id):
    return f"{prefix}:test_statistics:{test_id}"


def get_overall_score_cache_key(test_id, student_id):
    return f'overall_score_{test_id}_{student_id}'
