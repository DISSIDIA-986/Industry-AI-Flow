#!/usr/bin/env python3
"""
Import CSV datasets into vector database
Converts CSV files to text descriptions and imports them
"""

import sys
import os
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.services.document_loader import EnhancedDocumentLoader
from backend.services.chunker import chunk_text
from backend.services.embedder import embed_texts
from backend.services.vectorstore import VectorStore


def csv_to_text_description(csv_path: str) -> str:
    """Convert CSV file to text description"""
    df = pd.read_csv(csv_path)
    filename = Path(csv_path).stem

    # Generate comprehensive description
    description_parts = []

    # 1. Dataset metadata
    description_parts.append(f"Dataset: {filename}")
    description_parts.append(f"Total Records: {len(df)}")
    description_parts.append(f"Total Columns: {len(df.columns)}")
    description_parts.append("")

    # 2. Column information
    description_parts.append("Columns and Data Types:")
    for col in df.columns:
        dtype = str(df[col].dtype)
        description_parts.append(f"  - {col}: {dtype}")
    description_parts.append("")

    # 3. Sample statistics
    description_parts.append("Statistical Summary:")
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        stats = df[numeric_cols].describe()
        for col in numeric_cols[:10]:  # First 10 numeric columns
            description_parts.append(f"  {col}:")
            description_parts.append(f"    Mean: {stats[col]['mean']:.2f}")
            description_parts.append(f"    Min: {stats[col]['min']:.2f}")
            description_parts.append(f"    Max: {stats[col]['max']:.2f}")
    description_parts.append("")

    # 4. Categorical columns value counts
    categorical_cols = df.select_dtypes(include=['object']).columns
    if len(categorical_cols) > 0:
        description_parts.append("Categorical Data Distribution:")
        for col in categorical_cols[:5]:  # First 5 categorical columns
            value_counts = df[col].value_counts()
            description_parts.append(f"  {col}: {len(value_counts)} unique values")
            top_values = value_counts.head(5)
            for val, count in top_values.items():
                description_parts.append(f"    {val}: {count} ({count/len(df)*100:.1f}%)")
    description_parts.append("")

    # 5. Sample records
    description_parts.append("Sample Records (first 5):")
    for idx, row in df.head(5).iterrows():
        description_parts.append(f"\nRecord {idx + 1}:")
        for col in df.columns[:10]:  # First 10 columns
            description_parts.append(f"  {col}: {row[col]}")
    description_parts.append("")

    # 6. Data quality info
    description_parts.append("Data Quality:")
    description_parts.append(f"  Missing Values:")
    for col in df.columns:
        missing = df[col].isna().sum()
        if missing > 0:
            description_parts.append(f"    {col}: {missing} ({missing/len(df)*100:.1f}%)")
    description_parts.append("")

    # 7. Domain-specific insights
    if 'housing' in filename.lower():
        description_parts.append("Dataset Type: Real Estate / Housing Data")
        description_parts.append("Key Features: Property characteristics, pricing, location amenities")
    elif 'thyroid' in filename.lower():
        description_parts.append("Dataset Type: Medical / Clinical Data")
        description_parts.append("Key Features: Patient demographics, diagnosis, treatment outcomes")
    elif 'unemployment' in filename.lower():
        description_parts.append("Dataset Type: Economic / Labor Market Data")
        description_parts.append("Key Features: Employment statistics, demographics, temporal trends")

    return "\n".join(description_parts)


def import_csv_dataset(csv_path: str, vectorstore: VectorStore) -> dict:
    """Import a single CSV dataset"""
    print(f"\n{'='*60}")
    print(f"Processing: {Path(csv_path).name}")
    print(f"{'='*60}")

    try:
        # 1. Convert CSV to text
        print("🔄 Converting CSV to text description...")
        text_content = csv_to_text_description(csv_path)
        print(f"   Generated {len(text_content)} characters")

        # 2. Chunk text
        print("✂️ Chunking text...")
        chunks = chunk_text(text_content, chunk_size=800, chunk_overlap=100)
        print(f"   Created {len(chunks)} chunks")

        # 3. Embed chunks
        print("🔢 Generating embeddings...")
        chunk_contents = [c['content'] for c in chunks]
        embeddings = embed_texts(chunk_contents)
        print(f"   Generated {len(embeddings)} embeddings (dim: {len(embeddings[0])})")

        # 4. Store in vector database
        print("💾 Storing in vector database...")
        filename = Path(csv_path).name
        doc_id = vectorstore.store_document_with_chunks(
            filename=filename,
            filepath=csv_path,
            chunks=chunk_contents,
            embeddings=embeddings
        )

        print(f"✅ Successfully imported {Path(csv_path).name}")

        return {
            'filename': Path(csv_path).name,
            'chunks': len(chunks),
            'status': 'success'
        }

    except Exception as e:
        print(f"❌ Error importing {Path(csv_path).name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'filename': Path(csv_path).name,
            'status': 'failed',
            'error': str(e)
        }


def main():
    """Main import function"""
    print("\n" + "="*60)
    print("📊 CSV Dataset Import Tool")
    print("="*60)

    # Find CSV files
    datasets_dir = Path("datasets")
    csv_files = list(datasets_dir.glob("*.csv"))

    if not csv_files:
        print("❌ No CSV files found in datasets/ directory")
        return

    print(f"\n📁 Found {len(csv_files)} CSV files:")
    for f in csv_files:
        print(f"   - {f.name}")

    # Initialize vector store
    print("\n🔌 Connecting to vector database...")
    vectorstore = VectorStore()

    # Import each CSV
    results = []
    for csv_file in csv_files:
        result = import_csv_dataset(str(csv_file), vectorstore)
        results.append(result)

    # Summary
    print("\n" + "="*60)
    print("📊 Import Summary")
    print("="*60)

    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful

    print(f"Total files: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    total_chunks = sum(r.get('chunks', 0) for r in results if r['status'] == 'success')
    print(f"Total chunks imported: {total_chunks}")

    # Check final database state
    doc_count = vectorstore.get_document_count()
    chunk_count = vectorstore.get_chunk_count()

    print(f"\n📈 Database Status:")
    print(f"Total documents: {doc_count}")
    print(f"Total chunks: {chunk_count}")


if __name__ == "__main__":
    main()
