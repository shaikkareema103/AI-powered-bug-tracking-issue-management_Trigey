

@router.post("/live-duplicate-check", response_model=list[schemas.DuplicateCandidate])
def live_duplicate_check(
    payload: schemas.LiveDuplicateCheck,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    others = (
        db.query(models.Issue)
        .filter(models.Issue.project_id == payload.project_id)
        .order_by(models.Issue.created_at.desc())
        .limit(30)
        .all()
    )
    existing = [
        {"id": o.id, "number": o.number, "title": o.title, "description": o.description}
        for o in others
    ]
    try:
        candidates = ai_service.find_duplicates(payload.title, payload.description, existing)
    except Exception:
        return []
    return candidates
