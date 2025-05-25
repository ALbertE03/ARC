# Author Disambiguation: GCN vs Traditional Approaches

## Quick Start Guide

### Testing the Implementation

1. **Test the comparison between approaches:**

```bash
python test_gcn_comparison.py
```

2. **Run traditional consolidation:**

```bash
python enhanced_consolidation.py --method traditional --test-mode
```

3. **Run GCN consolidation (requires PyTorch):**

```bash
# Install PyTorch first
pip install torch

# Run GCN approach
python enhanced_consolidation.py --method gcn --test-mode --max-authors 500
```

4. **Run hybrid approach:**

```bash
python enhanced_consolidation.py --method hybrid --test-mode
```

### Installation for GCN Features

To use the GCN-based author disambiguation:

```bash
# Install PyTorch (CPU version)
pip install torch

# For GPU support (if you have CUDA)
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

## Method Comparison

### Traditional Rule-Based Approach

**Advantages:**

- ✅ Fast and lightweight
- ✅ Highly interpretable rules
- ✅ Conservative (high precision)
- ✅ No external dependencies
- ✅ Works well with limited data

**Disadvantages:**

- ❌ Requires manual rule tuning
- ❌ May miss subtle patterns
- ❌ O(n²) complexity for large datasets

### GCN-Based Approach

**Advantages:**

- ✅ Learns from data patterns
- ✅ Captures complex relationships
- ✅ Good generalization
- ✅ Scalable with proper hardware

**Disadvantages:**

- ❌ Requires PyTorch dependency
- ❌ Training time overhead
- ❌ Less interpretable
- ❌ May need more data

### Hybrid Approach

**Advantages:**

- ✅ Combines strengths of both methods
- ✅ Higher recall than traditional alone
- ✅ More robust than GCN alone
- ✅ Marks edges confirmed by both methods

**Disadvantages:**

- ❌ Longer execution time
- ❌ Requires all dependencies

## Performance Benchmarks

Based on testing with 500 authors:

| Method | Execution Time | Edges Found | Components | Precision | Recall |
|--------|---------------|-------------|------------|-----------|--------|
| Traditional | ~30s | ~50-100 | ~450-480 | High | Medium |
| GCN | ~120s | ~80-150 | ~400-450 | Medium | High |
| Hybrid | ~150s | ~100-200 | ~350-400 | High | High |

*Note: Actual performance varies with dataset characteristics*

## Configuration Recommendations

### For Small Datasets (< 1,000 authors)

```bash
python enhanced_consolidation.py --method traditional
```

### For Medium Datasets (1,000 - 10,000 authors)

```bash
python enhanced_consolidation.py --method gcn --max-authors 5000
```

### For Large Datasets (> 10,000 authors)

```bash
python enhanced_consolidation.py --method hybrid --save-to-db
```

### For Testing/Development

```bash
python enhanced_consolidation.py --method hybrid --test-mode --max-authors 100 --verbose
```

## Advanced Usage

### Custom GCN Parameters

Create a custom script with specific parameters:

```python
from models.GCN import create_gcn_matcher

gcn_matcher = create_gcn_matcher(
    embedding_dim=512,      # Larger embeddings
    hidden_dims=[256, 128], # Deeper network
    learning_rate=0.005,    # Slower learning
    margin=2.0,             # Larger margin
    device='cuda'           # GPU acceleration
)
```

### Custom Traditional Parameters

```python
from models.author_matcher import SmartAuthorMatcher

matcher = SmartAuthorMatcher(
    similarity_threshold=0.92,  # More aggressive
    batch_size=1000            # Larger batches
)
```

## Troubleshooting

### Common Issues

1. **"PyTorch not found" error:**

```bash
pip install torch
```

2. **CUDA out of memory:**

```bash
python enhanced_consolidation.py --method gcn --max-authors 100
```

3. **No consolidations found:**

- Check data quality
- Lower similarity thresholds
- Verify author name formats

4. **Slow performance:**

- Use `--max-authors` for testing
- Consider traditional method for quick results
- Use GPU for GCN if available

### Debug Mode

Enable detailed logging:

```bash
python enhanced_consolidation.py --method gcn --verbose --test-mode
```

Check the log file:

```bash
tail -f enhanced_consolidation.log
```

## Results Analysis

After running consolidation, check the results:

1. **Log files:** `enhanced_consolidation.log`
2. **Results summary:** `consolidation_results_*.json`
3. **Comparison results:** `consolidation_comparison_results.json`

### Example Results Summary

```json
{
  "method": "hybrid",
  "execution_time": 145.23,
  "total_edges": 187,
  "total_components": 378,
  "total_authors": 500,
  "traditional_edges": 92,
  "gcn_edges": 95,
  "timestamp": "2025-05-25 10:30:15"
}
```

## Next Steps

1. **Validate Results:** Manually check a sample of consolidations
2. **Tune Parameters:** Adjust thresholds based on your data
3. **Scale Up:** Test with larger datasets
4. **Deploy:** Use `--save-to-db` for production runs

## Support

For issues or questions:

1. Check the logs first
2. Try with `--test-mode` and smaller datasets
3. Review the GCN_README.md for detailed technical information
4. Use `--verbose` for detailed debugging output
