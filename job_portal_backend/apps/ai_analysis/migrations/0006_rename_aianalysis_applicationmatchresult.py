from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("ai_analysis", "0005_remove_aianalysis_candidate_embedding_version_and_more"),
        ("applications", "0005_remove_jobapplication_is_active"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="AIAnalysis",
            new_name="ApplicationMatchResult",
        ),
        migrations.AlterModelTable(
            name="applicationmatchresult",
            table="application_match_results",
        ),
        migrations.AlterField(
            model_name="applicationmatchresult",
            name="application",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="match_result",
                to="applications.jobapplication",
            ),
        ),
        migrations.RenameIndex(
            model_name="applicationmatchresult",
            old_name="ai_analyses_match_s_8f5f02_idx",
            new_name="app_match_score_idx",
        ),
        migrations.AlterModelOptions(
            name="applicationmatchresult",
            options={},
        ),
    ]
