# alembic/versions/xxxx_add_raw_results_and_new_tables.py
"""add raw results and new tables

Revision ID: xxxx
Revises: 
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'xxxx'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add raw_results column
    op.add_column('analysis_history', sa.Column('raw_results', JSONB, nullable=True))
    
    # Create new tables
    op.create_table(
        'analysis_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analysis_id', sa.Integer(), nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('metric_value', sa.Numeric(20, 2), nullable=True),
        sa.Column('metric_date', sa.Date(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('category_name', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analysis_history.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_analysis_metrics_type_value', 'metric_type', 'metric_value'),
        sa.Index('idx_analysis_metrics_category', 'category', 'category_name'),
    )
    
    op.create_table(
        'analysis_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analysis_id', sa.Integer(), nullable=False),
        sa.Column('insight_text', sa.Text(), nullable=False),
        sa.Column('insight_type', sa.String(50), nullable=False),
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analysis_history.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_analysis_insights_type', 'insight_type'),
    )
    
    op.create_table(
        'analysis_charts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analysis_id', sa.Integer(), nullable=False),
        sa.Column('chart_type', sa.String(50), nullable=False),
        sa.Column('chart_path', sa.String(255), nullable=True),
        sa.Column('chart_data', JSONB, nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analysis_history.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

def downgrade():
    op.drop_table('analysis_charts')
    op.drop_table('analysis_insights')
    op.drop_table('analysis_metrics')
    op.drop_column('analysis_history', 'raw_results')