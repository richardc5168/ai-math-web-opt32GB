# RBAC Test Cases: School-first

## Parent

1. Parent A fetches own child report -> 200
2. Parent A fetches Parent B child report -> 404 or 403
3. Parent A cannot see class aggregate endpoint -> 403
4. Parent A cannot list another parent's students -> 403

## Teacher

1. Teacher T1 lists own classes -> only T1 classes returned
2. Teacher T1 fetches own class report -> 200
3. Teacher T1 fetches T2 class report -> 404 or 403
4. Teacher T1 adds a student to own class -> 200
5. Teacher T1 adds T2-owned student to own class -> 404 or 403

## Admin

1. Admin lists all schools/classes/students -> 200
2. Missing admin token on admin dashboard endpoint -> 401
3. Admin can inspect teacher/class rollup across all schools -> 200

## Before/After Report Visibility

1. Parent sees only own child before/after
2. Teacher sees only students in class before/after
3. Admin sees all before/after rollups

## Traceability

1. Any before/after summary references source assessment ids
2. Any remediation suggestion references source weakness/event evidence