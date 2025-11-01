# ADR-003: PostgreSQL Direct Usage Over ORM Abstractions

**Date**: January 2025  
**Status**: Adopted  
**Decision**: Use asyncpg directly instead of SQLAlchemy ORM for simple queries

## Context

The initial RBAC implementation used SQLAlchemy ORM with complex model relationships. This created several issues:
- Compatibility problems between asyncpg and SQLAlchemy
- Overly complex code for simple queries
- Performance overhead from ORM abstractions
- Difficult debugging with multiple abstraction layers

## Decision

For simple database operations, use asyncpg directly:
1. Direct SQL queries with parameter binding
2. Simple result dictionaries instead of ORM models
3. Explicit connection management
4. Clear, readable SQL statements

## Rationale

1. **Simplicity**: Direct SQL is clearer for simple queries
2. **Performance**: Removes ORM overhead
3. **Compatibility**: Avoids asyncpg/SQLAlchemy conflicts
4. **Maintainability**: Easier to debug and understand

## Consequences

### Positive
- Cleaner, more readable code
- Better performance for simple queries
- Fewer compatibility issues
- Easier debugging

### Negative
- Loss of ORM features (migrations, relationships)
- More manual SQL writing
- Less type safety without models

### Neutral
- Still use SQLAlchemy for complex operations
- Hybrid approach based on complexity

## Implementation

### Before: ORM Complexity
```python
# Complex ORM setup for simple query
class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(UUID, ForeignKey("users.id"))
    role_id = Column(UUID, ForeignKey("roles.id"))
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")

# Query with joins and eager loading
result = session.query(UserRole).options(
    joinedload(UserRole.user),
    joinedload(UserRole.role)
).filter(UserRole.user_id == user_id).all()
```

### After: Direct SQL Simplicity
```python
# Simple, clear SQL
async with get_db_session() as conn:
    result = await conn.fetch(
        "SELECT role_id FROM user_roles WHERE user_id = $1",
        user_id
    )
    return [row['role_id'] for row in result]
```

## Alternatives Considered

1. **Full ORM**: Too heavy for simple queries
2. **Query Builder**: Still adds abstraction overhead
3. **Stored Procedures**: Less portable, harder to version

## Lessons Learned

"When choosing PostgreSQL as the 'fast approach', use it simply - don't recreate document DB complexity" 

Tools should be used for their strengths. PostgreSQL excels at relational queries with SQL. Adding layers of abstraction often negates these benefits.

## Guidelines

Use direct SQL when:
- Query is simple (< 10 lines)
- No complex relationships needed
- Performance is critical
- Clarity is important

Use ORM when:
- Complex object relationships
- Need migration management
- Building dynamic queries
- Type safety is critical

## References

- [PostgreSQL Simplicity Lessons](../postgresql-simplicity-lessons.md)
- [RBAC Simple Implementation](../../app/shared/rbac_simple.py)