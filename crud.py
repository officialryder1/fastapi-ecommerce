from fastapi import HTTPException
from models import *
from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction

async def get_products():
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
        'data': product_obj
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

async def get_product(id: int):
    product = await Product.get(id=id)
    if not product:
        raise HTTPException(status_code=404, detail="Product with ID not found")
    return product

# Retrieve data by business owner ID
async def retrieve_product_by_Business(user_id: int):
    user = await User.get(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User with ID do not exist.")
    
    business = await Business.get(owner=user)
    product = await Product.filter(business=business.id)

    return{
        'status': 'ok',
        'data': product
    }

# Add Order to db
async def add_order(order: order_pydanticIn,  product: id, user: user_pydantic): # type: ignore
    
    try:
        # Fetch user and product details
        user_obj = await User.get(id=user.id)
        product_order = await Product.get(id=product)
        
        # If product does not exist or is unavailable, raise an error
        if not product_order:
            return {'status': 'error', 'message': 'Product does not exist'}
        
        business_owner = product_order.business_id
        
        async with in_transaction():
            # Prepare order information
            order_info = order.dict(exclude_unset=True)
            order_info['buyer_id'] = user_obj.id
            order_info['owner_id'] = business_owner
            order_info['product_id'] = product_order.id

            # Create the order
            order_obj = await Order.create(**order_info)

            # Return the newly created order
            new_order = await order_pydantic.from_tortoise_orm(order_obj)

            return {
                'status': 'ok',
                'data': order_obj
            }

    except DoesNotExist:
        return {'status': 'error', 'message': 'User or Product does not exist'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    
async def order_by_user(user: user_pydantic):
    user_id = await User.get(id=user.id)
  

    if not user_id:
        raise HTTPException(status_code=404, detail="User with ID not found")
    
    order = await Order.filter(buyer=user_id)

    return {
        'status': 'ok',
        'data': order
    }

async def order_to_owner(user: user_detail_pydantic):
    user_id = await User.get(id = user.id)
    owner_id = await Business.get(owner=user_id)

    if not owner_id:
        raise HTTPException(status_code=404, detail="User with ID not found")
    
    order = await Order.filter(owner=owner_id)

    return {
        'status': 'ok',
        'data': order
    }


async def upload_user_detail(user_detail: user_detailIn_pydantic, user: user_pydantic):
    user_obj = await User.get(id=user.id)

    if not user_obj:
        raise HTTPException(status_code=404, detail="User with ID not found")
    user_detail_info = user_detail.dict(exclude_unset=True)
    user_detail_info['user_id'] = user_obj.id

    user_detail = await User_Detail.create(**user_detail_info)

    return {
        'status': 'ok',
        'data': user_detail
    }

async def get_shipping(id: int):
    user_detail = await User_Detail.get(id=id)

    if not user_detail:
        raise HTTPException(status_code=404, detail="User do not exist")
    return {
        'status': 'ok',
        'data': user_detail
    }

async def get_shipping_by_user(id: int):
    user_id = await User.get(id=id)

    if not user_id:
        raise HTTPException(status_code=404, detail="User with ID do not exist")
    
    shipping = await User_Detail.filter(user=user_id)

    return {
        'data': shipping
    }