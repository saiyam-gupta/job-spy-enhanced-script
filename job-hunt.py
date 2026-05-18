import csv
import re
import pandas as pd
from jobspy import scrape_jobs

# --- Search terms tailored to Saiyam's resume ---
# ~2 yrs exp | AWS Cloud Engineer @ Cvent | CDK, CloudFormation, Jenkins, Datadog
# Skills: AWS (EC2, Lambda, ECS, S3, IAM, SSM, CloudWatch), IaC, Python, Linux
search_terms = [
    # Direct title matches
    "cloud engineer",
    "cloud engineer AWS",
    "devops engineer",
    "devops engineer AWS",
    # Growing titles that match IaC + observability + automation skillset
    "platform engineer",
    "infrastructure engineer",
    "infrastructure engineer AWS",
    # Niche but high-signal for your CDK/CloudFormation/IaC expertise
    "cloud engineer CDK CloudFormation",
    # Observability & automation angle (Datadog, PagerDuty experience)
    "cloud operations engineer",
    # SRE roles
    "site reliability engineer",
    "SRE engineer",
    "SRE AWS",
]

# --- Title keywords that signal appropriate level (~1-3 yrs exp) ---
# Cloud Engineer, Cloud Engineer 1/2, DevOps Engineer, etc. are all fine
APPROPRIATE_TITLE_KEYWORDS = re.compile(
    r"\b(cloud|devops|dev[\s-]?ops|platform|infrastructure|sre|"
    r"site reliability|operations|automation)\b",
    re.IGNORECASE,
)

# --- Title keywords to EXCLUDE (too senior or irrelevant) ---
SENIOR_TITLE_EXCLUDE = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|director|architect|"
    r"head|vp|chief|iii|iv|level[\s-]?[3-9]|l[3-9]|"
    r"10\+?\s*years?|8\+?\s*years?|7\+?\s*years?|"
    r"data\s*scientist|data\s*analyst|business\s*analyst|"
    r"sales|marketing|recruiter|intern)\b",
    re.IGNORECASE,
)

# --- Description keywords that match your resume skills ---
RESUME_SKILL_KEYWORDS = re.compile(
    r"\b(aws|ec2|lambda|s3|ecs|iam|cloudformation|cdk|cloudwatch|"
    r"jenkins|datadog|terraform|ansible|docker|kubernetes|k8s|"
    r"python|linux|pagerduty|observability|infrastructure as code|"
    r"iac|ci[\s/]?cd|automation|cost optim|incident management)\b",
    re.IGNORECASE,
)

all_jobs = []

for term in search_terms:
    print(f"\n:mag: Searching for: {term}")
    try:
        jobs = scrape_jobs(
            site_name=["indeed", "linkedin", "google"],
            search_term=term,
            google_search_term=f"{term} jobs India",
            location="India",
            country_indeed="India",
            results_wanted=25,
            hours_old=24,  # 2 days
            description_format="markdown",
            verbose=1,
        )
        print(f"   Found {len(jobs)} jobs")
        all_jobs.append(jobs)
    except Exception as e:
        print(f"   Error searching '{term}': {e}")

if all_jobs:
    combined = pd.concat(all_jobs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["job_url"], keep="first")
    before = len(combined)

    # --- Filter out senior/irrelevant titles ---
    combined["is_senior"] = combined["title"].apply(
        lambda t: bool(SENIOR_TITLE_EXCLUDE.search(str(t)))
    )
    filtered = combined[~combined["is_senior"]].copy()
    filtered = filtered.drop(columns=["is_senior"])

    # --- Score jobs by resume skill match in description ---
    def skill_match_score(desc):
        if pd.isna(desc):
            return 0
        return len(RESUME_SKILL_KEYWORDS.findall(str(desc)))

    filtered["relevance_score"] = filtered["description"].apply(skill_match_score)

    # Sort by relevance score (descending), then date
    filtered = filtered.sort_values(
        ["relevance_score", "date_posted"],
        ascending=[False, False],
        na_position="last",
    )

    excluded = before - len(filtered)
    print(f"\n:bar_chart: Filtering: {before} total → {len(filtered)} relevant roles (excluded {excluded} senior/irrelevant)")

    # --- Keep only the most useful columns for the final export ---
    keep_columns = [
        "site",
        "title",
        "company",
        "location",
        "date_posted",
        "job_type",
        "is_remote",
        "job_level",
        "job_url",
        "company_url",
        "relevance_score",
    ]
    export_columns = [c for c in keep_columns if c in filtered.columns]
    output = filtered[export_columns].copy()

    output.to_csv(
        "jobs.csv",
        quoting=csv.QUOTE_NONNUMERIC,
        escapechar="\\",
        index=False,
    )
    output.to_excel("jobs.xlsx", index=False)

    print(f"\n:white_check_mark: Total relevant jobs found: {len(filtered)}")
    print(":page_facing_up: Saved to jobs.csv and jobs.xlsx")
    print(f"\nTop 20 results (sorted by skill match relevance):")
    cols = ["title", "company", "location", "relevance_score", "date_posted", "job_url"]
    available = [c for c in cols if c in output.columns]
    print(output[available].head(20).to_string(index=False))
else:
    print("\n:x: No jobs found.")