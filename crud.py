from fastapi import HTTPException
from models import *


async def get_product():
    products = await product_pydantic.from_queryset(Product.all())
    return {
        'status': 'ok',
        'data': products
    }

async def create_product(product: product_pydanticIn, user: user_pydantic): # type: ignore
    # Fetch the actual User ORM object (await it)
    user_obj = await User.get(id=user.id)
    
    # Get the Business associated with the user (await it)
    business = await Business.get(owner=user_obj)

    # Prepare the product data for creation
    product_info = product.dict(exclude_unset=True)
    product_info['business'] = business

    # Create the new product (await the ORM call)
    product_obj = await Product.create(**product_info)

    # Convert the newly created product to Pydantic format (await this too)
    new_product = await product_pydantic.from_tortoise_orm(product_obj)

    return {
        'status': 'ok',
        'data': new_product
    }

async def delete_product(id: int, user: user_pydantic):
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner

    if owner == user:
        await product.delete()
        return {
            'status': "ok",
            'message': "Product deleted"
            }
    else:
        raise HTTPException(status_code=403, detail="Not authorize to delete product")
    
async def update_product(id: int, product_data: product_pydanticIn, user: user_pydantic):
    # Check if product exist
    product = await Product.get(id=id)
    if not product:
        raise HTTPException(status_code=404, detail="Product with ID not found")
    
    # Check if the current user owns the business to which the product belongs
    business = await product.business
    owner = await business.owner

    if owner != user:
        raise HTTPException(status_code=403, detail="You are not allow to update this product")
    
    product_data_dict = product_data.dict(exclude_unset=True)
    await product.update_from_dict(product_data_dict)
    await product.save()

    updated_product = await product_pydantic.from_tortoise_orm(product)
    return {
        'status': 'ok',
        'data': updated_product
    }